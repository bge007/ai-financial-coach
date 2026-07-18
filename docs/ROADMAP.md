# Build Roadmap (8 phases)

Run phases in order via Claude Code slash commands (`/phase0` ... `/phase8`).
Check a box only once that phase's Definition of Done (in its command file
under `.claude/commands/`) is fully met and verified.

- [ ] **Phase 0 — Foundation & Auth** — FastAPI + React, LangGraph, Qdrant,
      Google OAuth multi-user, INR/India config
- [ ] **Phase 1 — Data & Profile** — CSV/PDF upload → parsed per-user
      financial profile
- [ ] **Phase 2 — Transactions** — auto-categorisation (rent, SIP, groceries,
      EMI, travel); rules first, LLM fallback
- [ ] **Phase 3 — Qdrant RAG + tabular tools** — per-user collections; typed
      query tools for exact aggregates
- [ ] **Phase 4 — Deterministic finance engines** — 50/30/20, risk
      allocation, mean-variance/Sharpe/frontier, tax old-vs-new, SIP/EPF/NPS
- [ ] **Phase 5 — Multi-agent layer** — LangGraph keyword router → Budget,
      Investment, Portfolio, Tax & Retirement, Debt agents
- [ ] **Phase 6 — API & dashboard** — FastAPI endpoints; React pages with
      streaming + MoM charts
- [ ] **Phase 7 — Eval, security & compliance** — engine tests vs known
      cases, PII encryption, FY-current tax slabs, disclaimers
- [ ] **Phase 8 — Deploy & monitor** — containerise, trace agent runs, watch
      cost + latency
