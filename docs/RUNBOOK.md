# Local runbook (hackathon)

## One-command local demo

```bash
cp .env.example .env
# Optional but recommended for richer chat:
#   OPENROUTER_API_KEY=sk-or-...
# AUTH_DISABLED=true is the default for demos (no Google setup).

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Qdrant: http://localhost:6333

## Demo journey
1. Open the UI (auto-authenticated as Demo User when `AUTH_DISABLED=true`).
2. Go to **Data & Profile** → upload `backend/tests/fixtures/hdfc_sample.csv`.
3. Open **Transactions**, **Dashboard**, **Analytics**, advisor pages.
4. **Ask the Coach** a question such as “prepay loan or invest surplus?”.

## Local dev without Docker

```bash
# terminal 1 — Qdrant
docker run --rm -p 6333:6333 qdrant/qdrant:v1.13.2

# terminal 2 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# terminal 3 — frontend
cd frontend
npm install && npm run dev
```

## Verify
```bash
cd backend && source .venv/bin/activate && pytest tests -q
cd frontend && npm run build
```

## Rollback
Stop Compose (`Ctrl+C` / `docker compose down`). Wipe demo data:

```bash
docker compose down -v
```

## Rotate keys
Update `.env` values for `SECRET_KEY` / `OPENROUTER_API_KEY` and recreate containers:

```bash
docker compose up --build -d
```

## Tax FY update
1. Copy `config/tax_fyYYYY_YY.yaml` from the latest CBDT / Budget notification.
2. Keep prior FY files for reproducibility.
3. Re-run `pytest backend/tests/test_engines.py -q`.
