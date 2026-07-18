"""OpenRouter LLM client with strict JSON + one repair retry."""

from __future__ import annotations

import json
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings

DISCLAIMER = "Informational only — not SEBI-registered investment advice."


class AgentOutput(BaseModel):
    summary: str
    recommendations: list[str] = Field(default_factory=list)
    figures_used: list[str] = Field(default_factory=list)


LLMFn = Callable[[str, str], Awaitable[str]]


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


async def call_agent_llm(
    system: str,
    user: str,
    *,
    llm: LLMFn | None = None,
) -> AgentOutput:
    """Validate AgentOutput JSON; exactly one repair attempt on failure."""
    fn = llm or default_openrouter_chat
    raw = await fn(system, user)
    try:
        return AgentOutput.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError, TypeError):
        repair_user = (
            user
            + "\n\nYour previous reply was invalid JSON. "
            "Return ONLY JSON: "
            '{"summary":"...","recommendations":["..."],"figures_used":["1234.00"]}'
        )
        raw2 = await fn(system, repair_user)
        try:
            return AgentOutput.model_validate(json.loads(raw2))
        except (json.JSONDecodeError, ValidationError, TypeError):
            return AgentOutput(
                summary=(
                    "I could not produce a reliable structured answer just now. "
                    "Please try again, or use the calculator pages for exact figures."
                ),
                recommendations=[],
                figures_used=[],
            )
