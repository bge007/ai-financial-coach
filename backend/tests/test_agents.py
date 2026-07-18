"""Phase 5 agent routing, LLM repair, guardrails, multi-agent merge."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_agents
from app.agents.guardrails import apply_guardrail, extract_rupee_figures
from app.agents.llm import AgentOutput, call_agent_llm
from app.agents.router import route_query
from app.core.db import SessionLocal
from app.models.user import User


ROUTING_CASES = [
    ("old vs new tax regime for me", ["tax_agent"]),
    ("claim 80c and nps", ["tax_agent"]),
    ("epf projection please", ["tax_agent"]),
    ("max sharpe portfolio", ["portfolio_agent"]),
    ("efficient frontier optimise", ["portfolio_agent"]),
    ("how should I invest my SIP", ["investment_agent"]),
    ("equity allocation by age", ["investment_agent"]),
    ("50/30/20 budget check", ["budget_agent"]),
    ("where am I overspending", ["budget_agent"]),
    ("expense analysis this month", ["budget_agent"]),
    ("should I prepay my loan", ["debt_agent"]),
    ("EMI payoff avalanche", ["debt_agent"]),
    ("hello how are you", ["coach_agent"]),
    ("explain my documents", ["coach_agent"]),
    (
        "prepay loan or invest surplus?",
        ["investment_agent", "debt_agent"],
    ),
]


@pytest.mark.parametrize("query,expected", ROUTING_CASES)
def test_routing_table(query, expected):
    routes = route_query(query)
    for agent in expected:
        assert agent in routes, f"{query} → {routes}, missing {agent}"


@pytest.mark.asyncio
async def test_llm_repair_then_safe_failure():
    calls = {"n": 0}

    async def bad_llm(system, user):
        calls["n"] += 1
        return "not-json"

    out = await call_agent_llm("sys", "user", llm=bad_llm)
    assert calls["n"] == 2  # original + one repair
    assert "grounded summary" in out.summary.lower() or "retry" in out.summary.lower()


@pytest.mark.asyncio
async def test_llm_valid_json_no_repair():
    calls = {"n": 0}

    async def good_llm(system, user):
        calls["n"] += 1
        return json.dumps(
            {
                "summary": "Your surplus is fine.",
                "recommendations": ["Keep SIPs"],
                "figures_used": ["10000.00"],
            }
        )

    out = await call_agent_llm("sys", "user", llm=good_llm)
    assert calls["n"] == 1
    assert out.figures_used == ["10000.00"]


@pytest.mark.asyncio
async def test_llm_connection_error_degrades_gracefully():
    async def raising_llm(system, user):
        raise ConnectionError("openrouter unreachable")

    # Must not raise; falls back to a safe grounded summary.
    out = await call_agent_llm("sys", "user", llm=raising_llm)
    assert "grounded summary" in out.summary.lower() or "retry" in out.summary.lower()
    assert out.figures_used == []


@pytest.mark.asyncio
async def test_llm_accepts_markdown_fenced_json():
    async def fenced_llm(system, user):
        return (
            "```json\n"
            '{"summary":"Allocate surplus to SIPs.","recommendations":["Keep SIPs"],'
            '"figures_used":["10000.00"]}\n'
            "```"
        )

    out = await call_agent_llm("sys", "user", llm=fenced_llm)
    assert out.summary == "Allocate surplus to SIPs."
    assert out.figures_used == ["10000.00"]


def test_guardrail_flags_invented_number():
    out = AgentOutput(
        summary="You should invest ₹999999 tomorrow.",
        recommendations=[],
        figures_used=["10000.00"],
    )
    guarded = apply_guardrail(out, financial_year="2026-27")
    assert guarded["guardrail_flagged"] is True
    assert "999999" in guarded["flagged_invented_numbers"]
    assert "[amount withheld]" in guarded["summary"]
    assert "not SEBI-registered" in guarded["summary"]
    assert "FY 2026-27" in guarded["summary"]


def test_guardrail_accepts_integer_form_of_engine_amount():
    """LLM often cites 40000 while engines store 40000.00."""
    out = AgentOutput(
        summary="Your SIP of ₹40000 can grow to ₹9058406.48 in 10 years from ₹100000.",
        recommendations=["Keep SIP at 40000 if surplus allows."],
        figures_used=["40000.00"],
    )
    guarded = apply_guardrail(
        out,
        financial_year="2026-27",
        allowed_figures=["40000.00", "9058406.48", "100000.00", "10.00"],
    )
    assert guarded["guardrail_flagged"] is False
    assert "[amount withheld]" not in guarded["summary"]
    assert "40000" in guarded["summary"]
    assert "9058406.48" in guarded["summary"]


def test_guardrail_accepts_allocation_percent_from_fraction():
    out = AgentOutput(
        summary="Portfolio is 28% equity and 16% cash with SIP ₹15000.00.",
        recommendations=[],
        figures_used=["0.28", "0.16", "15000.00"],
    )
    guarded = apply_guardrail(
        out,
        financial_year="2026-27",
        allowed_figures=["0.28", "0.16", "15000.00"],
    )
    # Bare 28 / 16 are not extracted as rupee figures; 15000.00 must pass.
    assert "15000.00" in guarded["summary"]
    assert "[amount withheld]" not in guarded["summary"] or guarded["guardrail_flagged"] is False


def test_guardrail_does_not_substring_replace_percentages():
    """Replacing invented '2' must not turn '28%' into '[amount withheld]8%'."""
    out = AgentOutput(
        summary="Mix is 28% equity. Do not invent ₹999999.",
        recommendations=[],
        figures_used=["0.28"],
    )
    guarded = apply_guardrail(out, financial_year="2026-27", allowed_figures=["0.28"])
    assert "28%" in guarded["summary"]
    assert "[amount withheld]8%" not in guarded["summary"]
    assert "[amount withheld]" in guarded["summary"]  # 999999 stripped


@pytest.mark.asyncio
async def test_multi_topic_merges_agents(client):
    async def fake_llm(system, user):
        return json.dumps(
            {
                "summary": "Use surplus carefully. Figure 49000.00 applies.",
                "recommendations": ["Compare EMI vs SIP"],
                "figures_used": ["49000.00"],
            }
        )

    async with SessionLocal() as db:
        user = User(google_sub="agent-u", email="agent@example.com", name="A")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        result = await run_agents(
            db,
            user.id,
            "prepay loan or invest surplus?",
            llm=fake_llm,
        )
    assert "debt_agent" in result["route"]
    assert "investment_agent" in result["route"]
    assert len(result["agent_outputs"]) >= 2
    assert "answer" in result


def test_ask_requires_auth(client):
    r = client.post("/api/ask", json={"query": "hello"})
    assert r.status_code == 401
