Implement Phase 5 — Multi-Agent Layer (LangGraph) — for the AI Financial
Coach project. Follow all conventions and principles in CLAUDE.md. Assumes
Phases 3-4 are complete (tabular tools, RAG retriever, and engines all exist
and are tested).

Implement the agent orchestration in `backend/app/agents/`.

TASKS:
1. `graph.py` — LangGraph StateGraph with state {user_id, query, route,
   tool_results, rag_chunks, answer, disclaimers}.
2. `router.py` — keyword-based routing node:
   tax|regime|80c|nps|epf → tax_agent; sharpe|portfolio|frontier|optimi →
   portfolio_agent; invest|sip|allocation|equity → investment_agent;
   budget|spend|50/30/20|expense → budget_agent; debt|emi|loan|payoff →
   debt_agent; else → coach_agent (general RAG chat). Keep the keyword map in
   config so it's tunable. If multiple agents match, run them and merge.
3. One node per agent. Each agent node: (a) calls its Phase 3 tabular tools
   and Phase 4 engine functions to gather numbers, (b) sends ONLY those
   computed results + retrieved RAG context to the LLM with a role-specific
   system prompt, (c) demands structured JSON output (summary,
   recommendations[], figures_used[]), validated by Pydantic with one repair
   retry.
4. Guardrail node before final answer: verify every ₹ number in the prose
   appears in figures_used (i.e., came from an engine); strip or flag any
   that don't; append the FY stamp and the standard disclaimer.
5. `POST /api/ask` — runs the graph, streams the answer (SSE).
   `POST /api/agents/{name}/analyze` — direct invocation for the advisor
   pages.

DEFINITION OF DONE (verify all before reporting done):
- Routing table test: 15 sample queries land on the expected agents.
- Agents run with a mocked LLM in tests; malformed output triggers exactly
  one repair attempt then a safe failure message.
- Guardrail test: an LLM response containing an invented number gets
  flagged.
- Multi-topic query ("prepay loan or invest surplus?") runs debt + investment
  agents and merges both.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 5, and summarize files changed and how to verify.
