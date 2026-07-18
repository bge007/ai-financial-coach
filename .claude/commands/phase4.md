Implement Phase 4 — Deterministic Finance Engines — for the AI Financial
Coach project. Follow all conventions and principles in CLAUDE.md, especially
principle 1 (LLM never computes numbers) and principle 2 (India constants in
versioned YAML).

Implement the quant core in `backend/app/engines/`. Pure functions, no LLM,
no I/O except reading config YAML. This phase is mostly tests.

TASKS:
1. `budget.py` — `fifty_thirty_twenty(income, spend_by_category)` -> needs/
   wants/savings actual vs target, per-category overshoot list. Maintain a
   category→bucket mapping in config.
2. `investment.py` — `risk_allocation(age, risk_profile)` -> {equity, debt,
   cash} bands (e.g., conservative/moderate/aggressive matrices in config);
   `project_growth(monthly_amount, years, expected_return)` using SIP future
   value: FV = P * [((1+i)^n - 1)/i] * (1+i), monthly compounding.
3. `portfolio.py` — given a returns DataFrame: mean-variance optimisation via
   PyPortfolioOpt (max Sharpe and min volatility portfolios), efficient
   frontier points, portfolio Sharpe ratio, and a 15-year corpus projection
   from optimised expected return. Include a data adapter that loads
   historical NAV/index returns from CSV (data source pluggable later).
4. `tax_india.py` — load `config/tax_fy*.yaml`; compute old vs new regime tax
   for a given gross income + deductions dict (80C, 80D, standard deduction,
   80CCD(1B)); apply slabs progressively + 4% cess; return side-by-side
   comparison and the better regime. `sip_maturity()`, `epf_projection(
   monthly, years, rate from config)`, `nps_projection()`.
5. `debt.py` — avalanche and snowball schedules: month-by-month amortisation,
   total interest paid, payoff date, given extra monthly surplus.

DEFINITION OF DONE (verify all before reporting done):
- Every engine has tests against hand-verified numbers (write the expected
  values in comments showing the arithmetic).
- Tax engine reproduces at least 4 known scenarios per regime to the rupee.
- Changing the YAML changes results with zero code edits.
- No engine imports anything from `app/agents` or calls an LLM.

When finished: run `pytest backend/tests -q`, update `docs/ROADMAP.md` to
check off Phase 4, and summarize files changed and how to verify.
