Implement Phase 2 — Transaction Auto-Categorization — for the AI Financial
Coach project. Follow all conventions and principles in CLAUDE.md. Assumes
Phase 1 is complete (Transaction model + upload pipeline exist).

CATEGORIES (enum): rent, sip_investment, groceries, emi, travel, utilities,
dining, shopping, salary, transfer, insurance, medical, entertainment,
education, other.

TASKS:
1. `backend/app/ingestion/categorizer.py`:
   Stage 1 — deterministic rules: regex/keyword map for Indian merchants and
   narration patterns (SWIGGY|ZOMATO→dining, IRCTC|MAKEMYTRIP|UBER|OLA→travel,
   "ACH.*SIP"|GROWW|ZERODHA|MF→sip_investment, NEFT.*SALARY→salary,
   BBPS|electricity|JIO|AIRTEL→utilities, EMI|LOAN→emi, DMART|BIGBASKET|
   BLINKIT→groceries, RENT→rent, etc.). Store rules as data, not code
   branches.
   Stage 2 — LLM fallback for uncategorized rows only: batch up to 50
   descriptions per call, request strict JSON {index: category}, validate
   with Pydantic, anything invalid → "other". Cache results by normalized
   description hash so repeat merchants never hit the LLM twice.
2. Run categorization automatically after upload; expose
   `POST /api/transactions/{id}/recategorize` for manual correction, and
   persist manual corrections as new highest-priority rules for that user.
3. `GET /api/transactions` with filters (month, category, direction, search)
   and pagination.
4. Frontend Transactions page: table with category chips, inline category
   editor, month filter.

DEFINITION OF DONE (verify all before reporting done):
- ≥80% of fixture transactions categorized by rules alone (measure in a test).
- LLM fallback path mocked in tests; malformed LLM JSON degrades to "other",
  never crashes.
- Manual correction persists and wins on next re-run.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 2, and summarize files changed and how to verify.
