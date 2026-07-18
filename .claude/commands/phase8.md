Implement Phase 8 — Deploy & Monitor — for the AI Financial Coach project.
Follow all conventions and principles in CLAUDE.md. Assumes Phase 7 is
complete (hardened, tested, secure).

Ship it.

TASKS:
1. Production Dockerfiles (multi-stage, non-root user); frontend served as
   static build behind the backend or a CDN.
2. Deploy config for one target (Fly.io / Render / a VPS with compose +
   Caddy for TLS). Managed or volume-backed Postgres and Qdrant with backups.
3. Observability: structured JSON logs, request IDs, LangSmith or Langfuse
   tracing on every agent run, per-run token cost logging, /metrics or a
   simple cost+latency dashboard.
4. GitHub Actions deploy workflow on tagged release; secrets via repo
   secrets.
5. `docs/RUNBOOK.md` — deploy, rollback, rotate keys, update tax YAML for a
   new FY (this will be needed every Union Budget).

DEFINITION OF DONE (verify all before reporting done):
- One-command (or one-tag) deploy from a clean clone.
- A production trace shows route, tools called, tokens, latency, cost.
- Runbook tested by following it verbatim.

When finished: update `docs/ROADMAP.md` to check off Phase 8 (project
complete), and summarize files changed and how to verify.
