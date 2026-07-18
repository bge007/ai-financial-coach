# MoneyMitra 🇮🇳

Your AI-powered financial companion for India — a full-stack, multi-agent advisor powered by **LangGraph** orchestration and **Qdrant** RAG.

> ⚠️ **Disclaimer:** This project is for informational and educational purposes only. It is not SEBI-registered investment advice.

## Features

- **Dashboard** — monthly income, expenses, surplus & debt at a glance, with a prioritised action plan
- **Data & Profile** — upload bank CSV or PDF statements, auto-parsed into a financial profile
- **Transactions** — AI-categorised transactions (rent, SIP, groceries, EMI, travel)
- **Analytics** — month-over-month spend tracking, category breakdown, income vs expense charts
- **Budget Advisor** — real-time 50/30/20 analysis, actual vs target
- **Investment Advisor** — risk-based allocation (equity/bonds/cash), 20-year growth projection
- **Portfolio Optimizer** — mean-variance optimisation, Sharpe ratio, efficient frontier, 15-year corpus projection
- **India Tax & Retirement** — old vs new regime comparison, SIP maturity, EPF & NPS projections
- **Ask the Coach** — RAG-powered chat grounded in your own documents, with full multi-agent orchestration

## Architecture

```
frontend (React)  ──►  backend (FastAPI)
                          │
                          ├── app/agents/     LangGraph router + 5 specialist agents
                          ├── app/engines/    deterministic quant engines (tax, MVO, SIP/EPF/NPS, budget)
                          ├── app/rag/        Qdrant per-user collections + retrieval
                          ├── app/ingestion/  CSV/PDF parsing + transaction categorisation
                          ├── app/api/        REST endpoints (upload, analyze, agents, dashboard)
                          ├── app/models/     Pydantic schemas + DB models
                          └── app/core/       auth (email/password + session JWT), config, security
```

**Design principle:** the LLM orchestrates and explains; **all financial numbers come from deterministic engines** in `app/engines/`. The model never invents a tax figure, Sharpe ratio, or projection.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React (Vite) |
| Backend | FastAPI (Python 3.11+) |
| Agents | LangGraph, keyword-based routing |
| RAG | Qdrant (per-user collections) |
| Auth | Email/password (demo), multi-user JWT cookie |
| Quant | pandas, numpy, PyPortfolioOpt / scipy |

## Hackathon quick start (local)

```bash
git clone https://github.com/<you>/ai-financial-coach.git
cd ai-financial-coach
cp .env.example .env
# Optional: set OPENROUTER_API_KEY for richer coach answers (works without it).
docker compose up --build
```

- UI: http://localhost:5173  
- API docs: http://localhost:8000/docs  
- Pre-login landing with **email/password** signup & login (`AUTH_DISABLED=false`). After auth you land on **Data & Profile**.

**Judge demo path:** Sign up / Log in → Data & Profile → upload `backend/tests/fixtures/hdfc_sample.csv` → Dashboard / Transactions / Analytics / advisors → Ask the Coach.

See [docs/RUNBOOK.md](docs/RUNBOOK.md) and [docs/PRIVACY.md](docs/PRIVACY.md).

> For an instant demo without signup, set `AUTH_DISABLED=true` (auto Demo User). Never enable that in production.

### Local dev (without Docker)

```bash
# qdrant
docker run --rm -p 6333:6333 qdrant/qdrant:v1.13.2

# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm install && npm run dev
```

## Configuration

- `config/tax_fy2026_27.yaml` — Indian tax slabs, 80C limits, EPF/NPS rates. **Versioned per financial year; never hardcode.**
- `.env` — API keys (LLM provider, Google OAuth client), Qdrant URL, DB URL.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the 8-phase build plan.

## Master specification

See [docs/MASTERPROMPT.md](docs/MASTERPROMPT.md) — a single self-contained
specification of the whole system (scope, principles, stack, data model,
engines, agents, API surface, and all 9 build phases). It is the narrative
companion to `CLAUDE.md` and enough to rebuild the project end to end.

## Building with Claude Code

This repo is set up as a Claude Code project:

- **`CLAUDE.md`** — persistent project memory (stack, non-negotiable
  principles, conventions). Loaded automatically every session.
- **`.claude/commands/`** — one slash command per build phase, plus utilities.

```bash
cd ai-financial-coach
claude
```

Then, in order:

```
/phase0   Foundation & Auth
/phase1   Data & Profile (ingestion)
/phase2   Transaction Auto-Categorization
/phase3   Qdrant RAG + Tabular Tools
/phase4   Deterministic Finance Engines
/phase5   Multi-Agent Layer (LangGraph)
/phase6   API & Live Dashboard
/phase7   Eval, Security & Compliance
/phase8   Deploy & Monitor
```

Utility commands:

```
/status            read-only progress report against docs/ROADMAP.md
/audit-isolation   run/extend the multi-user data isolation test suite
```

Each phase command carries its own Definition of Done — Claude Code should
verify it before declaring the phase complete. Recommended: one git branch
per phase, PR into `main`, paste the phase's DoD as the PR checklist.


## License

MIT
