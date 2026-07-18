import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../api/client.js";
import { formatINR } from "../utils/format.js";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet("/api/dashboard")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading dashboard…</p>;
  if (error) return <div className="banner error">{error}</div>;
  if (!data?.profile) {
    return (
      <div className="data-page">
        <h2>Dashboard</h2>
        <p className="muted empty-hint">Upload a statement on Data &amp; Profile to see your dashboard.</p>
      </div>
    );
  }

  const chartData = (data.trends || []).map((t) => ({
    month: t.month,
    income: Number(t.income),
    expenses: Number(t.expenses),
  }));

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Dashboard</h2>
        <p className="page-sub">Income, expenses, surplus and a prioritised action plan.</p>
      </header>
      <div className="profile-grid">
        {[
          ["Monthly income", data.profile.monthly_income],
          ["Monthly expenses", data.profile.monthly_expenses],
          ["Surplus", data.profile.surplus],
          ["EMI outgo", data.profile.emi_outgo],
          ["Total debt", data.profile.total_debt],
        ].map(([label, value]) => (
          <div className="metric" key={label}>
            <span className="metric-label">{label}</span>
            <span className="metric-value">{formatINR(value)}</span>
          </div>
        ))}
      </div>
      {chartData.length > 0 && (
        <section className="card" style={{ height: 280 }}>
          <h3>Trends</h3>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(v) => formatINR(v)} />
              <Bar dataKey="income" fill="#1a73e8" />
              <Bar dataKey="expenses" fill="#e8711a" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}
      <section className="card">
        <h3>Coach&apos;s action plan</h3>
        <ol className="action-list">
          {(data.actions || []).map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
