# Privacy & data retention

This project stores personal finance data for demo and educational use.

## What we store
- Account identity (Google subject / demo user email)
- Uploaded statement metadata (filename, SHA-256, size) — not logged in plaintext content
- Parsed transactions and derived financial profile
- Optional Qdrant document chunks from PDF uploads (payload-filtered by `user_id`)
- Category rules and LLM category-cache hashes (not raw PII logs)

## Retention
- Data remains until the user deletes it or the local database volume is wiped.
- Hackathon demos typically use ephemeral Docker volumes.

## Deletion
- `DELETE /api/me/data` removes the authenticated user's transactions, uploads,
  profile, category rules, and Qdrant points.
- The user account row is retained so login still works; re-upload starts clean.

## Logging
- Do not log raw statement contents, full narrations, or OAuth tokens.
- Prefer request IDs and aggregate counters.

## Encryption
- Local hackathon deploy: rely on host disk encryption + private Docker volumes.
- Production deployments should add at-rest encryption for SQLite/Qdrant volumes.

## Disclaimer
Informational only — not SEBI-registered investment advice.
