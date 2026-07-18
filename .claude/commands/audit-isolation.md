Run a multi-user data isolation audit per CLAUDE.md principle 3.

1. Enumerate every API endpoint in `backend/app/api/` that reads or writes
   user-scoped data (transactions, profile, uploads, agent/ask endpoints,
   RAG retrieval).
2. For each one, confirm there is a test that: creates two users (A, B),
   creates data for A, then asserts B cannot read/modify/list A's data via
   that endpoint (expect 401/403/404, never a 200 with A's data).
3. For any endpoint missing such a test, write it now.
4. For any endpoint that fails the isolation test, fix the underlying query
   to filter by the authenticated user_id and re-run.
5. Also check every Qdrant call in `backend/app/rag/` includes a user_id
   payload filter — grep for `.search(` / `.query(` calls without a filter
   and flag them.
6. Report a pass/fail table of endpoint -> isolation test status.
