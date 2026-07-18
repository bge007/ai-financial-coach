import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

export default function BudgetAdvisor() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiPost("/api/agents/budget_agent/analyze", {
      query: "Review my 50/30/20 budget",
      params: {},
    })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Analysing budget…</p>;
  if (error) return <div className="banner error">{error}</div>;

  const budget = data?.tool_results?.budget;
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
        <h2>Budget Advisor</h2>
        <p className="page-sub">50/30/20 actual vs target from your transactions.</p>
      </header>
      {!budget ? (
        <p className="muted empty-hint">Upload a statement to compute your budget split.</p>
      ) : (
        <section className="card" style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bucket" />
              <YAxis />
              <Tooltip formatter={(v) => formatINR(v)} />
              <Legend />
              <Bar dataKey="actual" fill="#e8711a" />
              <Bar dataKey="target" fill="#1a73e8" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}
      {data?.answer && (
        <section className="card">
          <h3>Coach notes</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{data.answer.summary}</p>
        </section>
      )}
    </div>
  );
}
