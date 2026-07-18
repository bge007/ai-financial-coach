Implement Phase 6 — API & Live Dashboard — for the AI Financial Coach
project. Follow all conventions and principles in CLAUDE.md. Assumes Phase 5
is complete (agents + /api/ask + /api/agents/{name}/analyze exist).

Complete the frontend against the finished backend.

PAGES:
1. Dashboard — income/expenses/surplus/debt stat cards, Coach's prioritised
   action plan (from a dashboard endpoint that runs budget + debt agents),
   sparkline trends.
2. Analytics — month-over-month bar chart (income vs expense), category
   donut, top-merchant list, month selector.
3. Budget Advisor — 50/30/20 actual-vs-target bars, overshoot callouts.
4. Investment Advisor — risk questionnaire (age, horizon, risk tolerance) →
   allocation pie + 20-year growth curve.
5. Portfolio Optimizer — efficient frontier scatter with max-Sharpe and
   min-vol points highlighted, weights table, 15-year corpus projection.
6. Tax & Retirement — income + deductions form → old vs new regime
   side-by-side with the winner highlighted; SIP/EPF/NPS projection cards.
7. Ask the Coach — chat UI with SSE streaming, source citations from RAG
   chunks, agent-route badge showing which specialist answered.

REQUIREMENTS:
- All amounts formatted in INR with Indian digit grouping (₹1,50,000).
- Loading/empty/error states for every page; empty state prompts upload.
- Disclaimer footer on every advisor page.
- Responsive enough to be usable on mobile.

DEFINITION OF DONE (verify all before reporting done):
- Full journey works: login → upload fixture statement → every page renders
  real derived data → chat answers with citations.
- `npm run build` passes in CI.

When finished: update `docs/ROADMAP.md` to check off Phase 6, and summarize
files changed and how to verify.
