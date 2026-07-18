"""Phase 2 categorizer tests: rules coverage, LLM fallback, cache, corrections."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import select

from app.ingestion.categorizer import (
    Categorizer,
    description_hash,
    normalize_description,
    parse_llm_category_json,
)
from app.ingestion.csv_parser import parse_csv
from app.models.category_cache import CategoryCache
from app.models.category_rule import CategoryRule
from app.models.enums import Category
from app.models.transaction import Transaction

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_descriptions() -> list[str]:
    descs: list[str] = []
    for name in ("hdfc_sample.csv", "icici_sample.csv", "sbi_sample.csv"):
        txns, _ = parse_csv((FIXTURES / name).read_bytes())
        descs.extend(t.description for t in txns)
    return descs


def test_rules_alone_cover_at_least_80_percent_of_fixtures():
    """≥80% of fixture narrations categorized by YAML rules (no LLM)."""
    cat = Categorizer(llm_batch=None)
    descriptions = _fixture_descriptions()
    assert descriptions

    hits = 0
    for desc in descriptions:
        if cat.match_rules(desc) is not None:
            hits += 1
    ratio = hits / len(descriptions)
    assert ratio >= 0.80, f"rules coverage {ratio:.1%} < 80% ({hits}/{len(descriptions)})"


def test_known_merchants_map_to_expected_categories():
    cat = Categorizer(llm_batch=None)
    cases = [
        ("SWIGGY BANGALORE", Category.dining),
        ("IRCTC TICKET BOOKING", Category.travel),
        ("ACH SIP GROWW BLUECHIP", Category.sip_investment),
        ("SALARY CREDIT NEFT ACME", Category.salary),
        ("BESCOM ELECTRICITY BBPS", Category.utilities),
        ("EMI HDFC LOAN", Category.emi),
        ("BIGBASKET GROCERY", Category.groceries),
        ("RENT PAYMENT UPI", Category.rent),
        ("AMAZON.IN PAYMENT", Category.shopping),
    ]
    for desc, expected in cases:
        assert cat.match_rules(desc) == expected, desc


def test_parse_malformed_llm_json_returns_empty():
    assert parse_llm_category_json("not json at all", 3) == {}
    assert parse_llm_category_json('{"0": "dining"}', 1) == {0: "dining"}


@pytest.mark.asyncio
async def test_llm_fallback_invalid_category_becomes_other(client):
    """Malformed / unknown LLM labels degrade to other, never crash."""

    async def bad_llm(descriptions):
        return {0: "not_a_real_category", 1: "dining"}

    # Force unknown narration past rules.
    cat = Categorizer(llm_batch=bad_llm)
    from app.core.db import SessionLocal

    async with SessionLocal() as db:
        results = await cat.categorize_many(
            ["XYZ UNKNOWN MERCHANT 999", "SWIGGY ORDER"],
            db,
            user_id=1,
            use_llm=True,
        )
    # First has no rule → LLM → other; second may hit dining via rules before LLM.
    assert results[0] == Category.other


@pytest.mark.asyncio
async def test_llm_cache_avoids_second_call(client):
    calls = {"n": 0}

    async def counting_llm(descriptions):
        calls["n"] += 1
        return {i: "other" for i in range(len(descriptions))}

    cat = Categorizer(llm_batch=counting_llm)
    from app.core.db import SessionLocal

    desc = "TOTALLY UNIQUE MERCHANT ABCXYZ"
    async with SessionLocal() as db:
        r1 = await cat.categorize_many([desc], db, user_id=1, use_llm=True)
        r2 = await cat.categorize_many([desc], db, user_id=1, use_llm=True)
    assert r1[0] == Category.other
    assert r2[0] == Category.other
    assert calls["n"] == 1


def test_manual_correction_wins_on_rerun(auth_client):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    up = auth_client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert up.status_code == 200

    listing = auth_client.get("/api/transactions?search=SWIGGY")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items
    txn = items[0]
    assert txn["category"] == "dining"

    # Manually correct dining → entertainment
    fixed = auth_client.post(
        f"/api/transactions/{txn['id']}/recategorize",
        json={"category": "entertainment"},
    )
    assert fixed.status_code == 200
    assert fixed.json()["transaction"]["category"] == "entertainment"

    # Re-run categorizer rules for same narration — user rule must win.
    cat = Categorizer(llm_batch=None)
    from app.core.db import SessionLocal
    import asyncio

    async def check():
        async with SessionLocal() as db:
            me = auth_client.get("/auth/me").json()
            result = await db.execute(
                select(CategoryRule).where(CategoryRule.user_id == me["id"])
            )
            rules = list(result.scalars().all())
            assert rules
            matched = cat.match_rules(txn["description"], rules)
            assert matched == Category.entertainment

    asyncio.run(check())


def test_normalize_and_hash_stable():
    a = normalize_description("  swiggy   bangalore ")
    b = normalize_description("SWIGGY BANGALORE")
    assert a == b
    assert description_hash("swiggy bangalore") == description_hash("SWIGGY BANGALORE")
