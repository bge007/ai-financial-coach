import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet, apiPost } from "../api/client.js";
import { COLORS } from "../theme.js";
import { formatINR } from "../utils/format.js";

function gapLine(label, actual, target) {
  const a = Number(actual) || 0;
  const t = Number(target) || 0;
  const diff = a - t;
  if (Math.abs(diff) < 1) {
    return `• ${label}: you are roughly on track at ${formatINR(a)} (suggested ${formatINR(t)}).`;
  }
  if (diff > 0) {
    return `• ${label}: you spent ${formatINR(a)}, about ${formatINR(diff)} more than the suggested ${formatINR(t)}.`;
  }
  return `• ${label}: you spent ${formatINR(a)}, about ${formatINR(-diff)} under the suggested ${formatINR(t)}.`;
}

function buildLaymanNotes(budget, income) {
  if (!budget?.actual || !budget?.target) return null;
  const needs = Number(budget.actual.needs) || 0;
  const wants = Number(budget.actual.wants) || 0;
  const savings = Number(budget.actual.savings) || 0;
  const incomeN = Number(income) || 0;

  const lines = [
    "In simple words:",
    "",
    "The 50/30/20 rule is a thumb rule for monthly money:",
    "• about 50% for needs (rent, groceries, bills, EMIs)",
    "• about 30% for wants (shopping, eating out, travel)",
    "• about 20% kept as savings / investments",
    "",
  ];

  if (incomeN > 0) {
    lines.push(`Your monthly income used here is ${formatINR(incomeN)}.`);
    lines.push("");
  }

  lines.push("Compared with that rule:");
  lines.push(gapLine("Needs", budget.actual.needs, budget.target.needs));
  lines.push(gapLine("Wants", budget.actual.wants, budget.target.wants));

  const savTarget = Number(budget.target.savings) || 0;
  if (savings <= 0 && savTarget > 0) {
    lines.push(
      `• Savings: nothing left to save right now. The rule suggests keeping about ${formatINR(savTarget)}.`
    );
  } else {
    lines.push(gapLine("Savings", budget.actual.savings, budget.target.savings));
  }

  lines.push("");
  if (needs > Number(budget.target.needs) && wants > Number(budget.target.wants)) {
    lines.push(
      "Bottom line: money going out for needs and wants is higher than the rule suggests, so savings are getting squeezed. Start by trimming a few wants (subscriptions, dining, shopping), then review big needs like EMIs or rent if possible."
    );
  } else if (savings < savTarget) {
    lines.push(
      "Bottom line: try to free up a little each month for savings — even a small SIP is better than zero."
    );
  } else {
    lines.push(
      "Bottom line: you are in a healthier range. Keep the habit and review this page after your next statement upload."
    );
  }

  if (budget.window) {
    lines.push("");
    lines.push(`(Figures are based on ${budget.window}.)`);
  }

  return lines.join("\n");
}

export default function BudgetAdvisor() {
  const [budget, setBudget] = useState(null);
  const [notes, setNotes] = useState(null);
  const [coachResult, setCoachResult] = useState(null);
  const [coachLoading, setCoachLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const dash = await apiGet("/api/dashboard");
        if (cancelled) return;
        const b = dash.budget || null;
        const inc = dash.profile?.monthly_income ?? null;
        setBudget(b);
        setNotes(buildLaymanNotes(b, inc));
        setLoading(false);

        // Coach result is additive — never overwrites the layman notes.
        setCoachLoading(true);
        apiPost("/api/agents/budget_agent/analyze", {
          query:
            "Explain my 50/30/20 budget in very simple layman language for a normal Indian salaried person. " +
            "Use short sentences. Avoid jargon. Start with what is going well or wrong in plain words, " +
            "then give 3 practical next steps. Do not invent numbers.",
          params: {},
        })
          .then((body) => {
            if (cancelled) return;
            const summary = body?.answer?.summary?.trim();
            const recs = body?.answer?.recommendations || [];
            if (summary) {
              setCoachResult({ summary, recommendations: recs });
            }
          })
          .catch(() => {
            /* keep layman notes only */
          })
          .finally(() => {
            if (!cancelled) setCoachLoading(false);
          });
      } catch (e) {
        if (!cancelled) {
          setError(e.message);
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="muted">Analysing budget…</p>;
  if (error) return <div className="banner error">{error}</div>;

  const chart = budget
    ? ["needs", "wants", "savings"].map((k) => ({
        bucket: k,
        actual: Number(budget.actual[k]),
        target: Number(budget.target[k]),
      }))
    : [];

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra</p>
        <h2>Budget Advisor</h2>
        <p className="page-sub">
          50/30/20 actual vs target from your transactions
          {budget?.window ? ` (${budget.window})` : ""}.
        </p>
      </header>
      {!budget ? (
        <p className="muted empty-hint">Upload a statement to compute your budget split.</p>
      ) : (
        <>
          <div className="profile-grid">
            {["needs", "wants", "savings"].map((k) => (
              <div className="metric" key={k}>
                <span className="metric-label">{k}</span>
                <span className="metric-value">{formatINR(budget.actual[k])}</span>
                <span className="metric-note">Target {formatINR(budget.target[k])}</span>
              </div>
            ))}
          </div>
          <section className="card" style={{ height: 320, marginTop: "1.15rem" }}>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip formatter={(v) => formatINR(v)} />
                <Legend />
                <Bar dataKey="actual" fill={COLORS.gold} />
                <Bar dataKey="target" fill={COLORS.primary} />
              </BarChart>
            </ResponsiveContainer>
          </section>
        </>
      )}

      {notes && (
        <section className="card coach-notes-card">
          <p className="step-label">Quick read</p>
          <h3>What this means</h3>
          <p className="coach-notes-text">{notes}</p>
        </section>
      )}

      <section className="card coach-notes-card">
        <p className="step-label">Coach result</p>
        <h3>Coach notes</h3>
        {coachLoading && (
          <div className="thinking-banner" role="status" aria-live="polite">
            <span className="thinking-dot" aria-hidden="true" />
            Thinking and Calculating…
          </div>
        )}
        {coachResult ? (
          <>
            <p className="coach-notes-text">{coachResult.summary}</p>
            {(coachResult.recommendations || []).length > 0 && (
              <div className="advisor-notes" style={{ marginTop: "0.85rem" }}>
                <h4>Practical next steps</h4>
                <ul className="action-list">
                  {coachResult.recommendations.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          !coachLoading && (
            <p className="muted">Coach tips will appear here after analysis.</p>
          )
        )}
      </section>
    </div>
  );
}
