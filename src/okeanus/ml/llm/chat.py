"""LLM chat endpoint with Gemini function-calling for ocean data queries."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from okeanus.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml"])

# In-memory conversation store (replace with Redis later)
_conversations: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_used: list[str]


def _build_gemini_tools(tool_defs: list[dict]) -> list:
    """Convert Anthropic-format tool definitions to Gemini FunctionDeclarations."""
    from google.genai import types

    declarations = []
    for t in tool_defs:
        declarations.append(
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=t.get("input_schema", {"type": "object", "properties": {}}),
            )
        )
    return [types.Tool(function_declarations=declarations)]


@router.post("/chat")
async def chat(req: ChatRequest) -> ChatResponse:
    """Chat with the ocean intelligence assistant."""
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    from google import genai
    from google.genai import types

    from okeanus.ml.llm.prompts import SYSTEM_PROMPT
    from okeanus.ml.llm.tools import TOOL_DEFINITIONS, execute_tool

    client = genai.Client(api_key=settings.gemini_api_key)
    tools = _build_gemini_tools(TOOL_DEFINITIONS)

    # Get or create conversation
    conv_id = req.conversation_id or str(uuid.uuid4())
    history = _conversations.get(conv_id, [])

    # Build messages: history + new user message
    contents = list(history) + [
        types.Content(role="user", parts=[types.Part.from_text(text=req.message)])
    ]

    tools_used: list[str] = []
    max_iterations = 10

    for _ in range(max_iterations):
        response = await client.aio.models.generate_content(
            model=settings.gemini_chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=SYSTEM_PROMPT,
            ),
        )

        # Collect function calls from response
        function_calls = [
            part for part in response.candidates[0].content.parts
            if part.function_call and part.function_call.name
        ]

        if not function_calls:
            # No tool calls — final text response
            break

        # Append assistant response to conversation
        contents.append(response.candidates[0].content)

        # Execute tools and build function response parts
        fn_response_parts = []
        for part in function_calls:
            fc = part.function_call
            tools_used.append(fc.name)
            try:
                result = await execute_tool(fc.name, dict(fc.args))
                # Ensure JSON-serializable
                result = json.loads(json.dumps(result, default=str))
            except Exception as exc:
                result = {"error": str(exc)}

            fn_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        # Send tool results back
        contents.append(types.Content(role="user", parts=fn_response_parts))

    # Extract text from final response
    try:
        text = response.text or ""
    except Exception:
        text = ""

    if not text:
        text = "I exceeded the maximum number of tool calls. Please try a simpler query."

    # Store conversation (keep last 20 turns)
    # Append the final assistant + user messages to history
    contents.append(response.candidates[0].content)
    _conversations[conv_id] = contents[-20:]

    return ChatResponse(response=text, conversation_id=conv_id, tools_used=tools_used)
