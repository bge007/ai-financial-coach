Implement Phase 3 — Qdrant RAG + Tabular Tools — for the AI Financial Coach
project. Follow all conventions and principles in CLAUDE.md. Assumes Phases
1-2 are complete (transactions exist and are categorized).

TASKS:
1. `backend/app/rag/store.py` — Qdrant client wrapper. Collection "user_docs"
   with mandatory payload field `user_id`; EVERY search call includes a
   `user_id` filter. Chunk uploaded PDFs/notes (500 tokens, 50 overlap),
   embed, upsert with metadata (source_file, page).
2. `backend/app/rag/retriever.py` — `retrieve(user_id, query, k=6)` returning
   chunks with scores + source metadata for citation.
3. `backend/app/agents/tools.py` — typed tabular tools (these are the ONLY
   way agents read financial numbers):
   - `get_profile(user_id)`
   - `monthly_summary(user_id, month)` -> income, expenses, surplus
   - `spend_by_category(user_id, month)` -> {category: amount}
   - `month_over_month(user_id, n_months)`
   - `list_debts(user_id)` -> [{name, outstanding, rate, emi}]
   - `recurring_payments(user_id)`
   Each backed by SQL/pandas aggregation, each with a docstring the router can
   surface, each unit-tested against fixtures.
4. Index documents into Qdrant automatically on upload (hook into the Phase 1
   upload endpoint).

DEFINITION OF DONE (verify all before reporting done):
- Cross-user isolation test: user A's query never returns user B's chunks.
- Tabular tool outputs match hand-computed fixture values exactly.
- Retrieval returns source metadata usable for citations.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 3, and summarize files changed and how to verify.
