import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet } from "../api/client.js";
import { CHART_PALETTE, COLORS } from "../theme.js";
import { formatINR, formatMonthLabel } from "../utils/format.js";

export default function Analytics() {
  const [data, setData] = useState(null);
  const [month, setMonth] = useState("all");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const q = month && month !== "all" ? `?month=${encodeURIComponent(month)}` : "?month=all";
    apiGet(`/api/analytics${q}`)
      .then((d) => {
        if (cancelled) return;
        setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [month]);

  if (loading && !data) return <p className="muted">Loading analytics…</p>;
  if (error) return <div className="banner error">{error}</div>;
  if (!data?.months?.length) {
    return (
      <div className="data-page">
        <header className="page-header">
          <p className="page-kicker">MoneyMitra</p>
          <h2>Analytics</h2>
        </header>
        <p className="muted empty-hint">Upload a statement to see month-over-month analytics.</p>
      </div>
    );
  }

  const scopeLabel =
    month === "all" || data.selected_summary?.label === "All months"
      ? "All months"
      : formatMonthLabel(data.selected_summary?.label || month);

  const mom = (data.month_over_month || []).map((t) => ({
    month: formatMonthLabel(t.month, { style: "short" }),
    income: Number(t.income),
    expenses: Number(t.expenses),
    highlight: month !== "all" && t.month === month,
  }));
  const cats = Object.entries(data.categories || {})
    .map(([name, value]) => ({
      name: name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: Number(value),
    }))
    .sort((a, b) => b.value - a.value);
  const catTotal = cats.reduce((sum, c) => sum + c.value, 0);
  const categoryChartHeight = Math.max(280, cats.length * 38 + 64);
  const summary = data.selected_summary;

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra</p>
        <h2>Analytics</h2>
        <p className="page-sub">Month-over-month spend, category mix, and top merchants.</p>
      </header>

      <div className="filters">
        <label>
          Month
          <select
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            disabled={loading}
          >
            <option value="all">All</option>
            {(data.months || []).map((m) => (
              <option key={m} value={m}>
                {formatMonthLabel(m)}
              </option>
            ))}
          </select>
        </label>
        {loading && <span className="muted">Updating…</span>}
      </div>

      {summary && (
        <div className="profile-grid" style={{ marginBottom: "1.15rem" }}>
          <div className="metric">
            <span className="metric-label">Income · {scopeLabel}</span>
            <span className="metric-value">{formatINR(summary.income)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Expenses · {scopeLabel}</span>
            <span className="metric-value">{formatINR(summary.expenses)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Surplus · {scopeLabel}</span>
            <span className="metric-value">{formatINR(summary.surplus)}</span>
          </div>
        </div>
      )}

      <section className="card" style={{ height: 300 }}>
        <h3>Income vs expenses</h3>
        <ResponsiveContainer width="100%" height="85%">
          <BarChart data={mom} key={`mom-${month}`}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(v) => formatINR(v)} />
            <Bar dataKey="income" name="income" fill={COLORS.primary} />
            <Bar dataKey="expenses" name="expenses" fill={COLORS.gold} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <div className="two-col">
        <section
          className="card analytics-category-card"
          style={{ minHeight: categoryChartHeight }}
        >
          <h3>Categories · {scopeLabel}</h3>
          {cats.length === 0 ? (
            <p className="muted">No debit categories for this selection.</p>
          ) : (
            <ResponsiveContainer width="100%" height={categoryChartHeight - 56} key={`cats-${month}-${cats.length}`}>
              <BarChart
                data={cats}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={(v) => formatINR(v)}
                  fontSize={11}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={96}
                  tick={{ fontSize: 12 }}
                  interval={0}
                />
                <Tooltip
                  formatter={(v) => {
                    const pct = catTotal > 0 ? ((Number(v) / catTotal) * 100).toFixed(1) : "0";
                    return `${formatINR(v)} (${pct}% of spend)`;
                  }}
                />
                <Bar dataKey="value" name="Spend" radius={[0, 6, 6, 0]} barSize={18}>
                  {cats.map((_, i) => (
                    <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="card">
          <h3>Top merchants · {scopeLabel}</h3>
          {(data.top_merchants || []).length === 0 ? (
            <p className="muted">No debit merchants for this selection.</p>
          ) : (
            <div className="table-wrap">
              <table className="txn-table merchant-table">
                <thead>
                  <tr>
                    <th>Merchant</th>
                    <th>Txns</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.top_merchants || []).map((m) => (
                    <tr key={`${m.name}-${m.count}-${m.amount}`}>
                      <td className="txn-desc" title={m.name}>
                        {m.name}
                      </td>
                      <td className="txn-amt">{m.count ?? 0}</td>
                      <td className="txn-amt">{formatINR(m.amount, { fixed: true })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
