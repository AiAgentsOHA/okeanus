"""Unified LLM client supporting Anthropic API and Claude CLI backends.

The ``claude_cli`` backend routes calls through the Claude Code CLI,
using the user's Max/Pro subscription instead of API credits.
Set ``LLM_PROVIDER=claude_cli`` in ``.env`` to activate.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Retry / timeout constants for Anthropic API calls
_API_TIMEOUT_SECONDS = 120
_API_MAX_RETRIES = 3
_API_BACKOFF_BASE = 2  # exponential backoff: 2s, 4s, 8s


async def call_llm(system: str, user_message: str) -> str:
    """Call LLM using the configured provider.

    Returns the model's text response.

    Raises ``RuntimeError`` on CLI failure or missing API key.
    """
    from okeanus.config import settings

    if settings.llm_provider == "claude_cli":
        return await _call_claude_cli(system, user_message, settings.llm_model)

    return await _call_anthropic(
        system, user_message, settings.llm_model, settings.llm_max_tokens,
    )


async def _call_anthropic(
    system: str, user_message: str, model: str, max_tokens: int,
) -> str:
    """Call Anthropic API directly (requires API key + credits).

    Includes explicit httpx timeout (120s) and retry with exponential
    backoff (3 attempts) to avoid hanging on CLOSE_WAIT connections.
    """
    from anthropic import AsyncAnthropic
    from okeanus.config import settings

    # Explicit httpx timeout prevents CLOSE_WAIT hangs
    timeout = httpx.Timeout(
        connect=30.0,
        read=_API_TIMEOUT_SECONDS,
        write=30.0,
        pool=30.0,
    )
    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=timeout,
    )

    last_exc: Exception | None = None
    for attempt in range(1, _API_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt < _API_MAX_RETRIES:
                delay = _API_BACKOFF_BASE ** attempt  # 2s, 4s
                logger.warning(
                    "Anthropic API attempt %d/%d failed (%s: %s), retrying in %ds",
                    attempt, _API_MAX_RETRIES, type(exc).__name__, exc, delay,
                )
                await asyncio.sleep(delay)
                # Create a fresh client to avoid reusing a broken connection
                client = AsyncAnthropic(
                    api_key=settings.anthropic_api_key,
                    timeout=timeout,
                )
            else:
                logger.error(
                    "Anthropic API failed after %d attempts: %s: %s",
                    _API_MAX_RETRIES, type(exc).__name__, exc,
                )
                raise RuntimeError(
                    f"Anthropic API call failed after {_API_MAX_RETRIES} retries: {exc}"
                ) from exc

    # Should not reach here, but satisfy type checker
    raise RuntimeError(f"Anthropic API call failed: {last_exc}")


async def _call_claude_cli(
    system: str, user_message: str, model: str,
) -> str:
    """Route LLM call through Claude Code CLI (uses Max subscription)."""
    model_alias = _resolve_model_alias(model)

    env = {**os.environ}
    env.pop("CLAUDECODE", None)      # allow invocation outside a running session
    env.pop("ANTHROPIC_API_KEY", None)  # force Max subscription, not API credits

    cmd = [
        "claude",
        "-p", user_message,
        "--system-prompt", system,
        "--model", model_alias,
        "--output-format", "text",
        "--no-session-persistence",
    ]

    logger.debug(
        "Claude CLI call: model=%s system_len=%d prompt_len=%d",
        model_alias, len(system), len(user_message),
    )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_API_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.error("Claude CLI timed out after %ds", _API_TIMEOUT_SECONDS)
        raise RuntimeError(
            f"Claude CLI timed out after {_API_TIMEOUT_SECONDS}s"
        )

    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error("Claude CLI failed (rc=%d): %s", proc.returncode, err)
        raise RuntimeError(f"Claude CLI error: {err}")

    result = stdout.decode().strip()
    logger.debug("Claude CLI response length: %d chars", len(result))
    return result


def _resolve_model_alias(model: str) -> str:
    """Map full model IDs to CLI-friendly aliases."""
    if "opus" in model:
        return "opus"
    if "haiku" in model:
        return "haiku"
    return "sonnet"
