Implement Phase 7 — Eval, Security & Compliance — for MoneyMitra
project. Follow all conventions and principles in CLAUDE.md. Assumes Phase 6
is complete (full product demoable end to end).

Harden the application.

TASKS:
1. Engine regression suite: golden-file tests for every engine (inputs +
   expected outputs committed as fixtures).
2. Agent eval set: 25 realistic Indian-finance queries with expected route
   and rubric checks (mentions correct FY, includes disclaimer, all numbers
   from engines). Run in CI with mocked LLM; provide a script to run against
   the live LLM manually.
3. Security pass: rate-limit auth + upload + ask endpoints; validate upload
   MIME/type/size; encrypt uploaded files at rest; scrub PII from logs
   (structlog processor); dependency audit (pip-audit, npm audit) in CI.
4. Isolation audit: parametrised test hitting every data endpoint as user A
   requesting user B's resources, expecting 403/404.
5. Data lifecycle: `DELETE /api/me/data` removes the user's rows, files, and
   Qdrant points; document retention policy in `docs/PRIVACY.md`.

DEFINITION OF DONE (verify all before reporting done):
- CI runs engines + agent evals + audits green.
- Isolation audit passes on all endpoints.
- Account data deletion verified by a test that finds zero residual
  rows/points.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 7, and summarize files changed and how to verify.
