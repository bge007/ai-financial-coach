import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../api/client.js";
import { formatINR } from "../utils/format.js";

const COLORS = ["#1a73e8", "#e8711a", "#0d9488", "#7c3aed", "#db2777", "#ca8a04", "#64748b", "#16a34a"];

export default function Analytics() {
  const [data, setData] = useState(null);
  const [month, setMonth] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const q = month ? `?month=${month}` : "";
    apiGet(`/api/analytics${q}`)
      .then((d) => {
        setData(d);
        if (!month && d.selected_month) setMonth(d.selected_month);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [month]);

  if (loading && !data) return <p className="muted">Loading analytics…</p>;
  if (error) return <div className="banner error">{error}</div>;
  if (!data?.months?.length) {
    return (
      <div className="data-page">
        <h2>Analytics</h2>
        <p className="muted empty-hint">Upload a statement to see month-over-month analytics.</p>
      </div>
    );
  }

  const mom = (data.month_over_month || []).map((t) => ({
    month: t.month,
    income: Number(t.income),
    expenses: Number(t.expenses),
  }));
  const cats = Object.entries(data.categories || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }));

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Analytics</h2>
        <p className="page-sub">Month-over-month spend, category mix, and top merchants.</p>
      </header>
      <div className="filters">
        <label>
          Month
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            {data.months.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
      </div>
      <section className="card" style={{ height: 300 }}>
        <h3>Income vs expenses</h3>
        <ResponsiveContainer width="100%" height="85%">
          <BarChart data={mom}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(v) => formatINR(v)} />
            <Bar dataKey="income" fill="#1a73e8" />
            <Bar dataKey="expenses" fill="#e8711a" />
          </BarChart>
        </ResponsiveContainer>
      </section>
      <div className="two-col">
        <section className="card" style={{ height: 300 }}>
          <h3>Categories</h3>
          {cats.length === 0 ? (
            <p className="muted">No debit categories this month.</p>
          ) : (
            <ResponsiveContainer width="100%" height="85%">
              <PieChart>
                <Pie data={cats} dataKey="value" nameKey="name" outerRadius={90} label>
                  {cats.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatINR(v)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>
        <section className="card">
          <h3>Top merchants</h3>
          <ul className="summary-list">
            {(data.top_merchants || []).map((m) => (
              <li key={m.name}>
                <span>{m.name}</span>
                <strong>{formatINR(m.amount)}</strong>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
