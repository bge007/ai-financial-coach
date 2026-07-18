Implement Phase 1 — Data & Profile (ingestion) — for the AI Financial Coach
project. Follow all conventions and principles in CLAUDE.md. Assumes Phase 0
is complete (auth + get_current_user dependency exist).

TASKS:
1. `backend/app/models/`: `Transaction` (id, user_id, date, description,
   amount, direction debit|credit, category nullable, source_file),
   `UploadedFile`, `FinancialProfile` (user_id, monthly_income,
   monthly_expenses, surplus, total_debt, emi_outgo, computed_at).
2. `backend/app/ingestion/csv_parser.py` — tolerant parser for common Indian
   bank CSV layouts (HDFC, ICICI, SBI style: date/narration/withdrawal/
   deposit/balance). Normalize to the Transaction schema. Handle dd/mm/yyyy,
   ₹ symbols, commas in amounts, and credit/debit column variants.
3. `backend/app/ingestion/pdf_parser.py` — pdfplumber table extraction for
   statement PDFs; fall back to line-regex parsing; reject unparseable files
   with a clear error.
4. `POST /api/upload` — accepts CSV/PDF, size limit 10 MB, stores parsed
   transactions for the current user, is idempotent (re-uploading the same
   file must not duplicate rows — hash the file), returns parse summary
   (rows parsed, rows skipped, date range).
5. `backend/app/engines/profile.py` — derive FinancialProfile deterministically:
   monthly income = median of monthly credit totals (exclude self-transfers),
   expenses = median monthly debits, surplus = income - expenses, EMI
   detection = recurring same-amount debits with EMI/LOAN keywords.
6. `GET /api/profile`. Frontend Data & Profile page: dropzone upload, parse
   summary, profile card.

DEFINITION OF DONE (verify all before reporting done):
- Fixture CSVs for 3 bank formats + 1 statement PDF parse correctly in tests.
- Duplicate upload adds zero new rows.
- Profile numbers match hand-computed values on fixtures exactly.
- A user cannot see another user's uploads (write and pass this test).

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 1, and summarize files changed and how to verify.
