import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet, apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

export default function BudgetAdvisor() {
  const [budget, setBudget] = useState(null);
  const [notes, setNotes] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const dash = await apiGet("/api/dashboard");
        if (cancelled) return;
        setBudget(dash.budget || null);
        setLoading(false);
        // Coach notes are optional / best-effort (LLM can be slow).
        apiPost("/api/agents/budget_agent/analyze", {
          query: "Review my 50/30/20 budget",
          params: {},
        })
          .then((body) => {
            if (!cancelled) setNotes(body?.answer || null);
          })
          .catch(() => {});
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
                <Bar dataKey="actual" fill="#D4AF37" />
                <Bar dataKey="target" fill="#0A2E5C" />
              </BarChart>
            </ResponsiveContainer>
          </section>
        </>
      )}
      {notes && (
        <section className="card">
          <h3>Coach notes</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{notes.summary}</p>
        </section>
      )}
    </div>
  );
}
