# Build Roadmap (9 phases: 0–8)

Run phases in order via Claude Code slash commands (`/phase0` ... `/phase8`).
Check a box only once that phase's Definition of Done (in its command file
under `.claude/commands/`) is fully met and verified.

- [x] **Phase 0 — Foundation & Auth** — FastAPI + React, LangGraph, Qdrant,
      Google OAuth multi-user, INR/India config
- [x] **Phase 1 — Data & Profile** — CSV/PDF upload → parsed per-user
      financial profile
- [x] **Phase 2 — Transactions** — auto-categorisation (rent, SIP, groceries,
      EMI, travel); rules first, LLM fallback
- [x] **Phase 3 — Qdrant RAG + tabular tools** — per-user collections; typed
      query tools for exact aggregates
- [x] **Phase 4 — Deterministic finance engines** — 50/30/20, risk
      allocation, mean-variance/Sharpe/frontier, tax old-vs-new, SIP/EPF/NPS
- [x] **Phase 5 — Multi-agent layer** — LangGraph keyword router → Budget,
      Investment, Portfolio, Tax & Retirement, Debt agents
- [x] **Phase 6 — API & dashboard** — FastAPI endpoints; React pages with
      streaming + MoM charts
- [x] **Phase 7 — Eval, security & compliance** — engine tests vs known
      cases, isolation audit, deletion, rate limits, PRIVACY.md
- [x] **Phase 8 — Deploy & monitor** — local Docker Compose, metrics/health,
      RUNBOOK.md
