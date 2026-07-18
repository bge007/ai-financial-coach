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
    try:
        return await fn(system, user)
    except Exception as exc:
        # Network/provider/auth failures degrade gracefully instead of 500.
        logger.warning("LLM call failed: %s: %s", type(exc).__name__, exc)
        return None


async def call_agent_llm(
    system: str,
    user: str,
    *,
    llm: LLMFn | None = None,
) -> AgentOutput:
    """Validate AgentOutput JSON; exactly one repair attempt on failure."""
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
