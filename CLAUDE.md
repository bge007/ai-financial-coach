# MoneyMitra — Claude Code Project Memory

This file is read automatically at the start of every Claude Code session in this
repo. It is the single source of truth for stack, principles, and conventions.
Do not restate or redecide these — follow them.

## What this is

A full-stack, multi-agent personal finance advisor for Indian users. LangGraph
orchestration, Qdrant RAG, FastAPI backend, React frontend.

## Fixed stack — do not substitute

- Backend: Python 3.11, FastAPI, SQLAlchemy (async) + SQLite (aiosqlite), Pydantic v2
- Agents: LangGraph, keyword-based routing (config-driven keyword map)
- RAG: Qdrant, one payload-filtered namespace per user
- Auth: Google OAuth via authlib, multi-user, JWT session cookie. A
  dev-only `AUTH_DISABLED` flag (default `true` in `.env.example`) bypasses
  login and auto-authenticates a fixed demo user via `get_current_user` —
  the OAuth flow and cookie enforcement stay fully implemented and are
  covered by tests with the flag off. Never set `AUTH_DISABLED=true` in
  production.
- Frontend: React (Vite), Recharts
- Quant: pandas, numpy, scipy, PyPortfolioOpt
- LLM: OpenRouter API (OpenAI-compatible; model set via `LLM_MODEL`, default
  `anthropic/claude-sonnet-4.5`), structured JSON outputs validated by Pydantic

## Non-negotiable principles

1. **The LLM never computes financial numbers.** Every ₹ figure, percentage,
   projection, tax amount, Sharpe ratio, or payoff schedule comes from
   deterministic Python in `backend/app/engines/`, unit-tested against known
   cases. The LLM only routes, explains, and personalizes. If you're about to
   have an LLM prompt produce a number, stop — write an engine function instead.
2. All India-specific constants (tax slabs, 80C/80D limits, EPF/NPS rates) live
   in versioned YAML under `config/tax_fy*.yaml`, keyed by financial year.
   Never hardcode them in Python. Every output using them states the FY.
3. Multi-user isolation is absolute: every DB query filters by `user_id`; every
   Qdrant query filters by user payload. Any new endpoint or tool touching user
   data needs a test proving user A cannot read user B's data. This holds
   regardless of `AUTH_DISABLED` — the demo user is still a `user_id` like any
   other and must not see a special-cased path around isolation.
4. Never log raw statement contents or PII. Currency is INR throughout,
   formatted with Indian digit grouping (₹1,50,000) in the frontend.
5. Every user-facing recommendation carries: "Informational only — not
   SEBI-registered investment advice."
6. Every phase/task: write code + tests, keep CI green, update
   `docs/ROADMAP.md` checkboxes, end with a summary of files changed and how
   to verify.

## Repo layout

```
backend/app/
  api/         REST endpoints
  agents/      LangGraph graph, router, per-agent nodes, tool definitions
  engines/     deterministic quant engines — no LLM calls, no I/O beyond config
  rag/         Qdrant client, chunking, retrieval
  ingestion/   CSV/PDF parsing, transaction categorization
  models/      SQLAlchemy models + Pydantic schemas
  core/        config, db session, auth
backend/tests/
config/       tax_fy*.yaml and other versioned India constants
frontend/src/
docs/         ROADMAP.md, PRIVACY.md, RUNBOOK.md
.claude/commands/   one slash command per build phase (see below)
```

## Build phases

The project is built in 9 phases (0–8), each with its own slash command in
`.claude/commands/`. Run them in order; each depends on the previous phase's
Definition of Done being met. Check `docs/ROADMAP.md` for current status before
starting a phase.

| # | Phase | Command |
|---|---|---|
| 0 | Foundation & Auth | `/phase0` |
| 1 | Data & Profile (ingestion) | `/phase1` |
| 2 | Transaction Auto-Categorization | `/phase2` |
| 3 | Qdrant RAG + Tabular Tools | `/phase3` |
| 4 | Deterministic Finance Engines | `/phase4` |
| 5 | Multi-Agent Layer (LangGraph) | `/phase5` |
| 6 | API & Live Dashboard | `/phase6` |
| 7 | Eval, Security & Compliance | `/phase7` |
| 8 | Deploy & Monitor | `/phase8` |

## Working conventions

- One git branch per phase (`phase-0-foundation`, `phase-1-ingestion`, ...),
  PR into `main`, paste the phase's Definition of Done as the PR checklist.
- Run `pytest backend/tests -q` and `npm run build` (in `frontend/`) before
  declaring a phase done.
- When adding a new engine function, write the expected value by hand in a
  comment showing the arithmetic, then assert against it — don't just assert
  against the function's own output.
- When adding a new agent or tool, add both a routing test (keyword → correct
  agent) and an isolation test (can't access another user's data).
- Prefer extending the keyword map / YAML config over adding new code branches
  for India-specific logic (bank formats, merchant categories, tax rules).

## Do not

- Do not let an LLM prompt template embed a computed number as a "default" or
  "example" that could leak into output.
- Do not add a new bank CSV format handler as a special case in code — add
  parsing rules as data where the existing parser can pick them up.
- Do not bypass the guardrail node in `agents/graph.py` that checks every ₹
  figure in an LLM response traces back to an engine call.
