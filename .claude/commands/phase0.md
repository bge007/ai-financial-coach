Implement Phase 0 — Foundation & Auth — for the MoneyMitra project.
Follow all conventions and principles in CLAUDE.md.

TASKS:
1. `backend/app/core/config.py` — pydantic-settings loading `.env` (DB URL,
   Qdrant URL, Google OAuth creds, OpenRouter key/base URL/model, SECRET_KEY,
   ENVIRONMENT).
2. `backend/app/core/db.py` — async SQLAlchemy engine + session dependency;
   alembic setup with an initial migration.
3. `backend/app/models/user.py` — User table (id, google_sub, email, name,
   created_at).
4. Google OAuth flow with authlib: `/auth/login`, `/auth/callback`, `/auth/me`,
   `/auth/logout`. Session via signed HTTP-only cookie (JWT). A
   `get_current_user` FastAPI dependency that 401s when unauthenticated.
5. Frontend: Vite React app with a login page (Google button), an
   authenticated shell with sidebar navigation stubs for: Dashboard,
   Data & Profile, Transactions, Analytics, Budget Advisor, Investment
   Advisor, Portfolio Optimizer, Tax & Retirement, Ask the Coach.
6. Wire `docker-compose.yml` so `docker compose up` brings up everything and
   the frontend can complete a login round-trip.

DEFINITION OF DONE (verify all before reporting done):
- `docker compose up` works end to end; `/health` returns ok.
- A real Google login creates a User row and `/auth/me` returns it.
- Unauthenticated API calls (except `/health`, `/auth/*`) return 401.
- Tests: config loads, auth dependency rejects missing/invalid tokens.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 0, and summarize files changed and how to verify.
