# AI Financial Coach — Master Prompt & Project Specification

> Single-document, self-contained specification of the entire project. Give this
> to any capable engineer or coding agent and they should be able to (re)build
> the system end to end without further context. It is the narrative companion to
> [`CLAUDE.md`](../CLAUDE.md) (machine-enforced rules), [`ROADMAP.md`](ROADMAP.md)
> (build status), and the per-phase commands in [`.claude/commands/`](../.claude/commands).

---

## 0. One-paragraph brief

Build a full-stack, multi-user, multi-agent **personal finance advisor for Indian
users**. A user signs in with Google, uploads bank statements (CSV/PDF), and the
system parses and categorizes their transactions, derives a financial profile,
and answers natural-language questions ("should I prepay my loan or invest the
surplus?", "old vs new tax regime for me?") through a LangGraph router that
dispatches to specialist agents. **Every rupee figure is computed by
deterministic Python engines** — the LLM only routes, retrieves, explains, and
personalizes. Numbers are grounded, cited, and stamped with the financial year;
every recommendation carries a "not SEBI-registered advice" disclaimer.

---

## 1. Product scope

### Personas
- **Primary:** salaried Indian individual (₹ income, SIPs, EMIs, 80C/80D
  deductions, EPF/NPS) who wants clear, grounded guidance without a human advisor.

### Core user journeys
1. **Onboard** — Google login → empty dashboard prompting an upload.
2. **Ingest** — drag-drop a bank CSV/PDF → transactions parsed, deduplicated,
   auto-categorized → a `FinancialProfile` (income, expenses, surplus, debt).
3. **Explore** — dashboards for analytics, budget (50/30/20), investments,
   portfolio optimization, tax & retirement.
4. **Ask** — chat grounded in the user's own data + documents, answered by the
   right specialist agent, with source citations and a route badge.

### Feature surface (maps 1:1 to sidebar + agents)
| Section | Backing engine(s) | Agent |
|---|---|---|
| Dashboard | budget + debt | (composite) |
| Data & Profile | ingestion + profile | — |
| Transactions | categorizer | — |
| Analytics | tabular tools | — |
| Budget Advisor | `budget.py` | budget_agent |
| Investment Advisor | `investment.py` | investment_agent |
| Portfolio Optimizer | `portfolio.py` | portfolio_agent |
| Tax & Retirement | `tax_india.py` | tax_agent |
| Ask the Coach | RAG + all tools | coach_agent (+ any) |

---

## 2. Non-negotiable principles

These are load-bearing. Violating any of them is a defect, not a style choice.

1. **The LLM never computes financial numbers.** Every ₹ figure, %, projection,
   tax amount, Sharpe ratio, or payoff schedule comes from deterministic Python
   in `backend/app/engines/`, unit-tested against hand-verified cases. The LLM
   routes, explains, personalizes — nothing more. If a prompt is about to produce
   a number, stop and write an engine function instead.
2. **India constants live in versioned YAML.** Tax slabs, 80C/80D limits,
   EPF/NPS rates → `config/tax_fy*.yaml`, keyed by financial year. Never hardcode
   in Python. Every output using them states the FY.
3. **Multi-user isolation is absolute.** Every DB query filters by `user_id`;
   every Qdrant query filters by user payload. Any new endpoint/tool touching
   user data ships with a test proving user A cannot read user B's data.
4. **Never log raw statement contents or PII.** Currency is INR throughout,
   formatted with Indian digit grouping (₹1,50,000) in the frontend.
5. **Every recommendation carries the disclaimer:** "Informational only — not
   SEBI-registered investment advice."
6. **Every phase:** code + tests, CI green, tick `docs/ROADMAP.md`, end with a
   summary of files changed and how to verify.

---

## 3. Fixed stack (do not substitute)

- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async) + **SQLite (aiosqlite)**,
  Pydantic v2, Alembic (async, `render_as_batch=True` for SQLite).
- **Agents:** LangGraph, keyword-based routing (config-driven keyword map).
- **RAG:** Qdrant, one payload-filtered namespace per user.
- **Auth:** Google OAuth via authlib, multi-user, JWT session cookie (HTTP-only).
- **Frontend:** React (Vite), Recharts.
- **Quant:** pandas, numpy, scipy, PyPortfolioOpt.
- **LLM:** **OpenRouter** (OpenAI-compatible SDK). Model via `LLM_MODEL`
  (default `anthropic/claude-sonnet-4.5`). Structured JSON validated by Pydantic.

> Historical note: the project originally specified Postgres + the Anthropic SDK.
> It now uses **SQLite** (single-file, zero-ops, fits the low-write hackathon
> profile) and **OpenRouter** (provider-flexible via one env var). All queries
> still filter by `user_id`; the database swap does not affect isolation.

---

## 4. Repository layout

```
backend/app/
  api/         REST endpoints (auth, upload, transactions, profile, ask, agents)
  agents/      LangGraph graph, router, per-agent nodes, tool definitions
  engines/     deterministic quant engines — no LLM, no I/O beyond config YAML
  rag/         Qdrant client, chunking, retrieval
  ingestion/   CSV/PDF parsing, transaction categorization
  models/      SQLAlchemy models + Pydantic schemas
  core/        config, db session, auth
backend/alembic/     async migrations (0001_create_users, ...)
backend/tests/       pytest suite (unit + isolation + eval)
config/              tax_fy*.yaml and other versioned India constants
frontend/src/        React app (pages/, components/)
docs/                ROADMAP.md, MASTERPROMPT.md, PRIVACY.md, RUNBOOK.md
.claude/commands/    one slash command per build phase (phase0..phase8) + utils
```

---

## 5. Data model (target end-state)

- **User**(id, google_sub[unique], email[unique], name, created_at)
- **UploadedFile**(id, user_id, filename, sha256[unique per user], size, uploaded_at)
- **Transaction**(id, user_id, date, description, amount, direction[debit|credit],
  category[nullable enum], source_file, created_at)
- **FinancialProfile**(user_id, monthly_income, monthly_expenses, surplus,
  total_debt, emi_outgo, computed_at)
- **CategoryRule**(id, user_id[nullable=global], pattern, category, priority) —
  manual corrections persist as highest-priority per-user rules.

**Category enum:** rent, sip_investment, groceries, emi, travel, utilities,
dining, shopping, salary, transfer, insurance, medical, entertainment,
education, other.

All user-scoped tables **must** filter by `user_id` in every query.

---

## 6. Deterministic engines (`backend/app/engines/`)

Pure functions. No LLM, no I/O except reading config YAML. Each has tests with
the expected value hand-written in a comment showing the arithmetic.

- **budget.py** — `fifty_thirty_twenty(income, spend_by_category)` → needs/wants/
  savings actual vs target + per-category overshoot. Category→bucket map in config.
- **investment.py** — `risk_allocation(age, risk_profile)` → {equity, debt, cash}
  from conservative/moderate/aggressive matrices in config; `project_growth(
  monthly, years, expected_return)` via SIP future value
  `FV = P · [((1+i)^n − 1)/i] · (1+i)`, monthly compounding.
- **portfolio.py** — mean-variance optimization via PyPortfolioOpt (max-Sharpe &
  min-volatility), efficient-frontier points, portfolio Sharpe, 15-year corpus
  projection. Pluggable CSV NAV/returns adapter.
- **tax_india.py** — load `config/tax_fy*.yaml`; old vs new regime for gross
  income + deductions (80C, 80D, standard deduction, 80CCD(1B)); progressive
  slabs + 4% cess; side-by-side + better regime. Plus `sip_maturity()`,
  `epf_projection()`, `nps_projection()`.
- **debt.py** — avalanche & snowball schedules: month-by-month amortization,
  total interest, payoff date, given extra monthly surplus.

**Guarantee:** changing the YAML changes results with zero code edits; no engine
imports from `app/agents` or calls an LLM.

---

## 7. RAG + tabular tools (`backend/app/rag/`, `backend/app/agents/tools.py`)

- **Qdrant store** — collection `user_docs`, mandatory payload field `user_id`;
  **every** search includes a `user_id` filter. Chunk uploaded PDFs/notes
  (~500 tokens, 50 overlap), embed, upsert with `{source_file, page}`.
- **retriever** — `retrieve(user_id, query, k=6)` → chunks + scores + source
  metadata for citation.
- **Tabular tools** are the ONLY way agents read financial numbers. Each is a
  typed function backed by SQL/pandas, docstringed, and unit-tested:
  `get_profile`, `monthly_summary`, `spend_by_category`, `month_over_month`,
  `list_debts`, `recurring_payments`.

---

## 8. Multi-agent layer (`backend/app/agents/`)

- **graph.py** — LangGraph `StateGraph`, state = {user_id, query, route,
  tool_results, rag_chunks, answer, disclaimers}.
- **router.py** — keyword map (in config, tunable):
  `tax|regime|80c|nps|epf → tax_agent`; `sharpe|portfolio|frontier|optimi →
  portfolio_agent`; `invest|sip|allocation|equity → investment_agent`;
  `budget|spend|50/30/20|expense → budget_agent`; `debt|emi|loan|payoff →
  debt_agent`; else `coach_agent`. Multiple matches → run all, merge.
- **agent nodes** — each: (a) calls its tabular tools + engine functions to
  gather numbers, (b) sends ONLY those computed results + RAG context to the LLM
  with a role-specific system prompt, (c) demands structured JSON
  `{summary, recommendations[], figures_used[]}`, Pydantic-validated with one
  repair retry, then a safe failure message.
- **guardrail node** — before final answer, verify every ₹ number in the prose
  appears in `figures_used` (i.e., came from an engine); strip/flag any that
  don't; append the FY stamp and the standard disclaimer.
- **endpoints** — `POST /api/ask` (SSE streaming), `POST /api/agents/{name}/analyze`.

---

## 9. API surface (target)

- `GET /health`
- `GET /auth/login` · `GET /auth/callback` · `GET /auth/me` · `POST /auth/logout`
- `POST /api/upload` (CSV/PDF, ≤10 MB, idempotent by file hash) → parse summary
- `GET /api/profile`
- `GET /api/transactions` (filters: month, category, direction, search; paged)
- `POST /api/transactions/{id}/recategorize`
- `POST /api/ask` (SSE) · `POST /api/agents/{name}/analyze`
- `GET /api/dashboard`
- `DELETE /api/me/data` (removes user's rows, files, Qdrant points)

All except `/health` and `/auth/*` require a valid session and return **401**
when unauthenticated, **403/404** when reaching across users.

---

## 10. Frontend (`frontend/src/`)

- Vite React SPA. Login page (Google button) → authenticated shell with a
  sidebar of 9 sections. Dev server proxies `/auth`, `/api`, `/health` to the
  backend so the HTTP-only session cookie is same-origin.
- Pages (built in Phase 6): Dashboard, Analytics (MoM bars, category donut,
  top merchants), Budget (50/30/20 actual-vs-target), Investment (risk
  questionnaire → allocation pie + 20y growth curve), Portfolio (efficient
  frontier scatter + weights table + 15y corpus), Tax & Retirement (income +
  deductions form → old-vs-new side-by-side + SIP/EPF/NPS cards), Ask the Coach
  (SSE chat + citations + agent-route badge).
- **Requirements:** INR Indian digit grouping (₹1,50,000); loading/empty/error
  states everywhere (empty prompts upload); disclaimer footer on advisor pages;
  usable on mobile.

---

## 11. Build phases (run in order; each gated on the previous DoD)

| # | Phase | Deliverable | Key DoD |
|---|---|---|---|
| 0 | Foundation & Auth | FastAPI+React skeleton, async SQLAlchemy+SQLite, Alembic, Google OAuth + JWT cookie, `get_current_user`, sidebar shell | login round-trip; non-auth calls 401; config + auth tests |
| 1 | Data & Profile | Transaction/UploadedFile/FinancialProfile models, tolerant CSV parser (HDFC/ICICI/SBI), pdfplumber PDF parser, idempotent `/api/upload`, profile engine | 3 CSV + 1 PDF fixtures parse; dup upload adds 0 rows; profile matches hand-computed; cross-user test |
| 2 | Categorization | data-driven rules first, batched LLM fallback (strict JSON, cached by hash), manual correction persists as user rule | ≥80% by rules alone; malformed LLM JSON → "other", never crashes; correction wins on re-run |
| 3 | RAG + tools | Qdrant store (user_id filter), retriever w/ citations, 6 typed tabular tools, index docs on upload | cross-user isolation; tool outputs match fixtures; citations usable |
| 4 | Engines | budget, investment, portfolio, tax_india, debt | tests vs hand-verified numbers; tax = 4 known scenarios/regime to the rupee; YAML change alters results, no code edits; no LLM imports |
| 5 | Multi-agent | LangGraph graph, keyword router, agent nodes, guardrail, `/api/ask` (SSE) | 15-query routing test; mocked LLM + one repair retry; guardrail flags invented numbers; multi-topic merges agents |
| 6 | API & Dashboard | all 7 React pages against finished backend | full journey login→upload→every page renders real data; `npm run build` green |
| 7 | Eval, Security, Compliance | engine golden tests, 25-query agent eval, rate limits, upload validation, encryption at rest, PII log scrubbing, isolation audit, `DELETE /api/me/data` + PRIVACY.md | CI green on engines+evals+audits; isolation audit passes all endpoints; deletion leaves zero residue |
| 8 | Deploy & Monitor | prod Dockerfiles (multi-stage, non-root), one deploy target, tracing (LangSmith/Langfuse) + token cost, tagged-release deploy, RUNBOOK.md | one-tag deploy from clean clone; prod trace shows route/tools/tokens/latency/cost; runbook verified verbatim |

**Status:** Phase 0 complete (see [ROADMAP.md](ROADMAP.md)). Phases 1–8 pending.

---

## 12. Working conventions

- One git branch per phase (`phase-0-foundation`, `phase-1-ingestion`, …),
  PR into `main`, paste the phase's DoD as the PR checklist.
- Gate every phase on `pytest backend/tests -q` and `npm run build` (frontend).
- New engine function → write the expected value by hand in a comment showing
  the arithmetic, then assert against it (not against the function's own output).
- New agent/tool → add both a routing test (keyword → agent) and an isolation
  test (cannot access another user's data).
- Prefer extending the keyword map / YAML config over new code branches for
  India-specific logic (bank formats, merchant categories, tax rules).

## 13. Do not

- Let an LLM prompt template embed a computed number as a "default"/"example"
  that could leak into output.
- Add a new bank CSV format as a special case in code — add parsing rules as
  data the existing parser picks up.
- Bypass the guardrail node that checks every ₹ figure traces to an engine call.

---

## 14. Environment & run

`.env` (from `.env.example`): `DATABASE_URL` (sqlite+aiosqlite), `QDRANT_URL`,
`GOOGLE_CLIENT_ID/SECRET`, `OAUTH_REDIRECT_URI`, `OPENROUTER_API_KEY`,
`OPENROUTER_BASE_URL`, `LLM_MODEL`, `SECRET_KEY`, `ENVIRONMENT`, `FRONTEND_URL`.

```bash
docker compose up --build          # frontend :5173, backend :8000/docs, qdrant :6333
# or local dev:
cd backend && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Verify a phase: `pytest backend/tests -q` and (Phase 6+) `npm run build`.
