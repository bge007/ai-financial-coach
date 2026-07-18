"""RAG isolation + tabular tool exactness tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.agents import tools
from app.core.db import SessionLocal
from app.models.enums import Category, Direction
from app.models.financial_profile import FinancialProfile
from app.models.transaction import Transaction
from app.models.user import User
from app.rag.embeddings import FakeEmbedder
from app.rag.store import DocumentStore, set_store
from app.rag.retriever import retrieve

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def memory_store():
    store = DocumentStore(
        client=QdrantClient(location=":memory:"),
        embedder=FakeEmbedder(dim=384),
        collection="user_docs_test",
    )
    set_store(store)
    yield store
    set_store(None)


def test_rag_cross_user_isolation(memory_store):
    memory_store.upsert_chunks(
        user_id=1,
        source_file="a.pdf",
        chunks=[("User A secret SIP of one lakh", 1)],
    )
    memory_store.upsert_chunks(
        user_id=2,
        source_file="b.pdf",
        chunks=[("User B grocery budget notes", 1)],
    )

    hits_a = retrieve(user_id=1, query="SIP investment", k=6)
    assert hits_a
    assert all(h.user_id == 1 for h in hits_a)
    assert all("User B" not in h.text for h in hits_a)
    assert hits_a[0].source_file == "a.pdf"
    assert hits_a[0].page == 1

    hits_b = retrieve(user_id=2, query="grocery", k=6)
    assert hits_b
    assert all(h.user_id == 2 for h in hits_b)
    assert all("User A" not in h.text for h in hits_b)


@pytest.mark.asyncio
async def test_tabular_tools_match_hand_computed(client):
    """Hand math on a known mini ledger.

    Jan 2026:
      credit salary 100000
      debit rent 25000, groceries 5000 → expenses 30000, surplus 70000
    Feb 2026:
      credit salary 100000
      debit rent 25000 → expenses 25000, surplus 75000
    """
    async with SessionLocal() as db:
        user = User(google_sub="tools-user", email="tools@example.com", name="T")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        rows = [
            (date(2026, 1, 1), "SALARY", "100000", Direction.credit, Category.salary),
            (date(2026, 1, 5), "RENT", "25000", Direction.debit, Category.rent),
            (date(2026, 1, 10), "DMART", "5000", Direction.debit, Category.groceries),
            (date(2026, 2, 1), "SALARY", "100000", Direction.credit, Category.salary),
            (date(2026, 2, 5), "RENT", "25000", Direction.debit, Category.rent),
            (date(2026, 1, 15), "EMI HDFC LOAN", "15000", Direction.debit, Category.emi),
            (date(2026, 2, 15), "EMI HDFC LOAN", "15000", Direction.debit, Category.emi),
        ]
        for d, desc, amt, direction, cat in rows:
            db.add(
                Transaction(
                    user_id=user.id,
                    date=d,
                    description=desc,
                    amount=Decimal(amt),
                    direction=direction,
                    category=cat,
                    source_file="t.csv",
                )
            )
        db.add(
            FinancialProfile(
                user_id=user.id,
                monthly_income=Decimal("100000"),
                monthly_expenses=Decimal("40000"),
                surplus=Decimal("60000"),
                total_debt=Decimal("0"),
                emi_outgo=Decimal("15000"),
            )
        )
        await db.commit()

        profile = await tools.get_profile(db, user.id)
        assert profile["monthly_income"] == Decimal("100000.00")

        # Jan: income 100000; expenses 25000+5000+15000=45000; surplus 55000
        jan = await tools.monthly_summary(db, user.id, "2026-01")
        assert jan["income"] == Decimal("100000.00")
        assert jan["expenses"] == Decimal("45000.00")
        assert jan["surplus"] == Decimal("55000.00")

        # spend_by_category Jan debits only
        by_cat = await tools.spend_by_category(db, user.id, "2026-01")
        assert by_cat["rent"] == Decimal("25000.00")
        assert by_cat["groceries"] == Decimal("5000.00")
        assert by_cat["emi"] == Decimal("15000.00")

        mom = await tools.month_over_month(db, user.id, n_months=2)
        assert len(mom) == 2
        assert mom[0]["month"] == "2026-01"
        assert mom[1]["month"] == "2026-02"

        debts = await tools.list_debts(db, user.id)
        assert debts
        assert debts[0]["emi"] == Decimal("15000.00")
        assert debts[0]["outstanding"] is None

        recurring = await tools.recurring_payments(db, user.id)
        assert any(r["amount"] == Decimal("25000.00") for r in recurring)
        assert any(r["amount"] == Decimal("15000.00") for r in recurring)

        # Isolation: another user sees empty aggregates
        other = await tools.monthly_summary(db, user.id + 999, "2026-01")
        assert other["income"] == Decimal("0.00")
