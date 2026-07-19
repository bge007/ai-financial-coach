"""OpenRouter LLM client with strict JSON + one repair retry."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DISCLAIMER = "Informational only — not SEBI-registered investment advice."

_last_llm_error: str | None = None


def get_last_llm_error() -> str | None:
    return _last_llm_error


class AgentOutput(BaseModel):
    summary: str
    recommendations: list[str] = Field(default_factory=list)
    figures_used: list[str] = Field(default_factory=list)


LLMFn = Callable[[str, str], Awaitable[str]]


def _parse_agent_json(raw: str) -> AgentOutput:
    """Parse AgentOutput from raw LLM text, tolerating markdown fences."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text, count=1)
        text = text.strip()
    try:
        return AgentOutput.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError):
        # Last resort: extract the outermost JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return AgentOutput.model_validate(json.loads(text[start : end + 1]))
        raise


async def default_openrouter_chat(system: str, user: str) -> str:
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openrouter_api_key:
        # Hackathon/demo fallback: deterministic JSON from context (no invented maths).
        return json.dumps(
            {
                "summary": (
                    "Here is a grounded summary based on your computed finance figures. "
                    "Set OPENROUTER_API_KEY for fuller natural-language coaching."
                ),
                "recommendations": [
                    "Review the figures on the advisor pages",
                    "Upload recent statements for fresher data",
                ],
                "figures_used": [],
            }
        )
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        timeout=60.0,
        default_headers={
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "MoneyMitra",
        },
    )
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


async def _safe_call(fn: LLMFn, system: str, user: str) -> str | None:
    """Call the LLM; return None on transport/provider errors (never raise)."""
    global _last_llm_error
    try:
        return await fn(system, user)
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        msg = str(exc).lower()
        exc_name = type(exc).__name__
        if status_code == 401 or "401" in msg or "user not found" in msg or "authentication" in exc_name.lower():
            _last_llm_error = (
                "OpenRouter rejected the API key (401). "
                "Create a valid key at openrouter.ai/keys, update .env, and restart the backend."
            )
        elif status_code == 402 or "insufficient" in msg or "credit" in msg:
            _last_llm_error = (
                "OpenRouter account has insufficient credits. Add credits at openrouter.ai/settings."
            )
        elif status_code == 429 or "rate limit" in msg:
            _last_llm_error = "OpenRouter rate limit hit — wait a moment and try again."
        elif exc_name in {"APIConnectionError", "ConnectError", "ConnectTimeout"} or (
            "connection" in msg and "401" not in msg
        ):
            _last_llm_error = (
                "Could not connect to OpenRouter — check your internet, then restart the backend."
            )
        elif status_code:
            _last_llm_error = f"OpenRouter error ({status_code}): {str(exc)[:120]}"
        else:
            _last_llm_error = f"Language model error ({exc_name}): {str(exc)[:120]}"
        logger.warning("LLM call failed: %s: %s", exc_name, exc)
        return None


async def call_agent_llm(
    system: str,
    user: str,
    *,
    llm: LLMFn | None = None,
) -> AgentOutput:
    """Validate AgentOutput JSON; exactly one repair attempt on failure."""
    global _last_llm_error
    _last_llm_error = None
    fn = llm or default_openrouter_chat
    raw = await _safe_call(fn, system, user)
    if raw is not None:
        try:
            return _parse_agent_json(raw)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            repair_user = (
                user
                + "\n\nYour previous reply was invalid JSON. "
                "Return ONLY JSON: "
                '{"summary":"...","recommendations":["..."],"figures_used":["1234.00"]}'
            )
            raw2 = await _safe_call(fn, system, repair_user)
            if raw2 is not None:
                try:
                    return _parse_agent_json(raw2)
                except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                    pass
    return AgentOutput(
        summary=(
            "I could not reach the language model just now, so here is a grounded "
            "summary from your computed finance figures. Please retry for fuller "
            "natural-language coaching."
        ),
        recommendations=[],
        figures_used=[],
    )


async def consultation_expert_reply(system: str, user: str) -> tuple[str, str | None]:
    """Plain-text finance expert reply for premium consultation chat."""
    global _last_llm_error
    _last_llm_error = None
    fn = default_openrouter_chat_plain
    raw = await _safe_call(fn, system, user)
    if raw:
        return raw.strip(), None
    warning = _last_llm_error or "Language model unavailable — showing guidance from your profile only."
    fallback = (
        "I'm having trouble reaching the expert AI right now. "
        "Please check your OpenRouter key and try again. "
        "Meanwhile, review your Budget Advisor and Dashboard for deterministic figures."
    )
    return fallback, warning


async def default_openrouter_chat_plain(system: str, user: str) -> str:
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openrouter_api_key:
        return (
            "I'm your MoneyMitra finance expert (offline mode). "
            "Set OPENROUTER_API_KEY for full AI answers. "
            "Based on your booking topic, start with the Budget Advisor 50/30/20 view "
            "and upload a recent statement so I can reference your real income and spends."
        )
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        timeout=60.0,
        default_headers={
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "MoneyMitra Consultation",
        },
    )
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.35,
    )
    return (resp.choices[0].message.content or "").strip()
