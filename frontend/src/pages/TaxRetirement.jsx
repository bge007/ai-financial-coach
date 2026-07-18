import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

function buildTaxNotes(tax) {
  if (!tax) return null;
  const better = tax.better_regime === "either" ? "either regime" : `${tax.better_regime} regime`;
  const lines = [
    "In simple words:",
    "",
    `For FY ${tax.financial_year}, old-regime tax is ${formatINR(tax.old_total_tax)} and ` +
      `new-regime tax is ${formatINR(tax.new_total_tax)}.`,
    `The lower bill is under the ${better}` +
      (Number(tax.savings_vs_other) > 0
        ? ` — about ${formatINR(tax.savings_vs_other)} less than the other option.`
        : "."),
  ];
  lines.push("");
  lines.push(
    "Bottom line: pick the regime with the lower total tax for your numbers. " +
      "This is a planning estimate from the finance engines, not a filing instruction."
  );
  return lines.join("\n");
}

function buildRetirementNotes(tax) {
  if (!tax) return null;
  const lines = [
    "In simple words:",
    "",
    `From age ${tax.age} to ${tax.retirement_age} (${tax.years_to_retire} years), ` +
      `your EPF, NPS, and current corpus project to about ${formatINR(tax.retirement_corpus)}.`,
    `That breaks down as EPF ${formatINR(tax.epf_corpus)}, NPS ${formatINR(tax.nps_corpus)}, ` +
      `plus grown starting corpus from ${formatINR(tax.current_corpus)}.`,
  ];
  if (tax.annual_expense_need != null && Number(tax.annual_expense_need) > 0) {
    lines.push(
      `At today's spend level, yearly expenses are about ${formatINR(tax.annual_expense_need)} — ` +
        "use that as a rough check against the projected corpus."
    );
  }
  lines.push("");
  lines.push(
    "Bottom line: raise EPF/NPS or the starting corpus if the projected pot feels thin for your lifestyle."
  );
  return lines.join("\n");
}

function CalculatorIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4" y="2" width="16" height="20" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
      <rect x="7" y="5" width="10" height="3.5" rx="1" fill="currentColor" opacity="0.35" />
      <circle cx="8.2" cy="12" r="1.1" fill="currentColor" />
      <circle cx="12" cy="12" r="1.1" fill="currentColor" />
      <circle cx="15.8" cy="12" r="1.1" fill="currentColor" />
      <circle cx="8.2" cy="15.8" r="1.1" fill="currentColor" />
      <circle cx="12" cy="15.8" r="1.1" fill="currentColor" />
      <circle cx="15.8" cy="15.8" r="1.1" fill="currentColor" />
      <circle cx="8.2" cy="19.4" r="1.1" fill="currentColor" />
      <rect x="10.6" y="18.4" width="5.8" height="2" rx="1" fill="currentColor" />
    </svg>
  );
}

export default function TaxRetirement() {
  const [annualIncome, setAnnualIncome] = useState("1200000");
  const [oldDeductions, setOldDeductions] = useState("150000");
  const [age, setAge] = useState("30");
  const [retirementAge, setRetirementAge] = useState("60");
  const [monthlyExpenses, setMonthlyExpenses] = useState("40000");
  const [currentCorpus, setCurrentCorpus] = useState("500000");
  const [monthlyEpf, setMonthlyEpf] = useState("12000");
  const [monthlyNps, setMonthlyNps] = useState("5000");
  const [data, setData] = useState(null);
  const [mode, setMode] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [profileLoaded, setProfileLoaded] = useState(false);

  useEffect(() => {
    apiGet("/api/user-profile")
      .then((body) => {
        if (!body) return;
        if (body.age != null) setAge(String(body.age));
        if (body.monthly_income != null) {
          setAnnualIncome(String(Math.round(Number(body.monthly_income) * 12)));
        }
        if (body.monthly_expenses != null) {
          setMonthlyExpenses(String(body.monthly_expenses));
        }
        if (body.emergency_fund != null) {
          setCurrentCorpus(String(body.emergency_fund));
        }
      })
      .catch(() => {})
      .finally(() => setProfileLoaded(true));
  }, []);

  async function run(nextMode) {
    setLoading(true);
    setError(null);
    setMode(nextMode);
    try {
      const body = await apiPost("/api/agents/tax_agent/analyze", {
        query:
          nextMode === "retirement"
            ? "Project my retirement corpus with EPF and NPS"
            : "Compare old vs new tax regime for my income",
        params: {
          mode: nextMode,
          gross_income: Number(annualIncome) || 0,
          old_regime_deductions: Number(oldDeductions) || 0,
          age: Number(age) || 30,
          retirement_age: Number(retirementAge) || 60,
          monthly_expenses: Number(monthlyExpenses) || 0,
          current_corpus: Number(currentCorpus) || 0,
          monthly_epf: Number(monthlyEpf) || 0,
          monthly_nps: Number(monthlyNps) || 0,
        },
      });
      setData(body);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const tax = data?.tool_results?.tax;
  const activeMode = mode || tax?.mode || "tax";
  const engineNotes =
    tax && activeMode === "retirement" ? buildRetirementNotes(tax) : buildTaxNotes(tax);
  const coachSummary = data?.answer?.summary || "";
  const showCoach = Boolean(coachSummary) && !coachSummary.includes("[amount withheld]");
  const fyLabel = tax?.financial_year || "2026-27";

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">Financial command centre</p>
        <h2>Tax &amp; Retirement</h2>
        <p className="page-sub">
          Compare old and new income-tax regimes and project EPF / NPS retirement corpus
          using versioned FY {fyLabel} rules.
        </p>
      </header>

      <div className="advisor-layout">
        <section className="card advisor-form-card">
          <div className="advisor-form-head">
            <div className="advisor-icon" aria-hidden="true">
              <CalculatorIcon />
            </div>
            <div>
              <h3>India Tax &amp; Retirement</h3>
              <p className="step-sub" style={{ marginBottom: 0 }}>
                Compare old and new income-tax regimes using versioned FY {fyLabel} rules.
              </p>
            </div>
          </div>

          <form
            className="advisor-form"
            onSubmit={(e) => {
              e.preventDefault();
              run("tax");
            }}
          >
            <label className="field">
              <span>Annual income</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={annualIncome}
                onChange={(e) => setAnnualIncome(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Old-regime deductions</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={oldDeductions}
                onChange={(e) => setOldDeductions(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Current age</span>
              <input
                type="number"
                min="18"
                max="100"
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Retirement age</span>
              <input
                type="number"
                min="40"
                max="80"
                value={retirementAge}
                onChange={(e) => setRetirementAge(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Monthly expenses</span>
              <input
                type="number"
                min="0"
                step="500"
                value={monthlyExpenses}
                onChange={(e) => setMonthlyExpenses(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Current corpus</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={currentCorpus}
                onChange={(e) => setCurrentCorpus(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Monthly EPF</span>
              <input
                type="number"
                min="0"
                step="100"
                value={monthlyEpf}
                onChange={(e) => setMonthlyEpf(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Monthly NPS</span>
              <input
                type="number"
                min="0"
                step="100"
                value={monthlyNps}
                onChange={(e) => setMonthlyNps(e.target.value)}
              />
            </label>

            <button
              className="primary-btn advisor-run-btn"
              type="submit"
              disabled={loading}
            >
              {loading && activeMode === "tax" ? "Comparing…" : "Compare tax regimes"}
            </button>
            <button
              className="secondary-btn advisor-run-btn"
              type="button"
              disabled={loading}
              onClick={() => run("retirement")}
            >
              {loading && activeMode === "retirement"
                ? "Projecting…"
                : "Project retirement corpus"}
            </button>
          </form>
          {!profileLoaded && <p className="muted">Loading saved profile defaults…</p>}
        </section>

        <section className="card advisor-output-card">
          <p className="step-label">Auditable result</p>
          <h3>Analysis output</h3>

          {error && <div className="banner error">{error}</div>}

          {!tax && !error && (
            <div className="advisor-empty">
              Enter assumptions and run the analysis. Results are computed by
              deterministic Python tools.
            </div>
          )}

          {tax && activeMode === "tax" && (
            <div className="advisor-results">
              <div className="profile-grid">
                <div className={`metric ${tax.better_regime === "old" ? "winner" : ""}`}>
                  <span className="metric-label">Old regime tax</span>
                  <span className="metric-value">{formatINR(tax.old_total_tax)}</span>
                </div>
                <div className={`metric ${tax.better_regime === "new" ? "winner" : ""}`}>
                  <span className="metric-label">New regime tax</span>
                  <span className="metric-value">{formatINR(tax.new_total_tax)}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">Better regime</span>
                  <span className="metric-value">{tax.better_regime}</span>
                  <span className="metric-note">
                    Saves {formatINR(tax.savings_vs_other)} · FY {tax.financial_year}
                  </span>
                </div>
              </div>

              {engineNotes && (
                <div className="advisor-notes">
                  <h4>Result description</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{engineNotes}</p>
                </div>
              )}

              {showCoach && (
                <div className="advisor-notes" style={{ marginTop: "0.85rem" }}>
                  <h4>Coach notes</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{coachSummary}</p>
                </div>
              )}
            </div>
          )}

          {tax && activeMode === "retirement" && (
            <div className="advisor-results">
              <div className="profile-grid">
                <div className="metric">
                  <span className="metric-label">Projected retirement corpus</span>
                  <span className="metric-value">{formatINR(tax.retirement_corpus)}</span>
                  <span className="metric-note">
                    {tax.years_to_retire}y · age {tax.age} → {tax.retirement_age}
                  </span>
                </div>
                <div className="metric">
                  <span className="metric-label">EPF corpus</span>
                  <span className="metric-value">{formatINR(tax.epf_corpus)}</span>
                  <span className="metric-note">SIP {formatINR(tax.monthly_epf)}/mo</span>
                </div>
                <div className="metric">
                  <span className="metric-label">NPS corpus</span>
                  <span className="metric-value">{formatINR(tax.nps_corpus)}</span>
                  <span className="metric-note">SIP {formatINR(tax.monthly_nps)}/mo</span>
                </div>
              </div>

              {engineNotes && (
                <div className="advisor-notes">
                  <h4>Result description</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{engineNotes}</p>
                </div>
              )}

              {showCoach && (
                <div className="advisor-notes" style={{ marginTop: "0.85rem" }}>
                  <h4>Coach notes</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{coachSummary}</p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
