"""LLM chat endpoint with Claude tool-use for ocean data queries."""

from __future__ import annotations

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


@router.post("/chat")
async def chat(req: ChatRequest) -> ChatResponse:
    """Chat with the ocean intelligence assistant."""
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    import anthropic

    from okeanus.ml.llm.prompts import SYSTEM_PROMPT
    from okeanus.ml.llm.tools import TOOL_DEFINITIONS, execute_tool

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Get or create conversation
    conv_id = req.conversation_id or str(uuid.uuid4())
    messages = _conversations.get(conv_id, [])
    messages.append({"role": "user", "content": req.message})

    tools_used: list[str] = []
    max_iterations = 10  # Safety limit

    for _ in range(max_iterations):
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    try:
                        result = await execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                    except Exception as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {exc}",
                            "is_error": True,
                        })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Final text response
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            messages.append({"role": "assistant", "content": response.content})
            break
    else:
        text = "I exceeded the maximum number of tool calls. Please try a simpler query."

    # Store conversation (keep last 20 messages to prevent unbounded growth)
    _conversations[conv_id] = messages[-20:]

    return ChatResponse(response=text, conversation_id=conv_id, tools_used=tools_used)
