import { useState } from "react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

const COLORS = ["#1a73e8", "#0d9488", "#ca8a04"];

export default function InvestmentAdvisor() {
  const [age, setAge] = useState(30);
  const [risk, setRisk] = useState("moderate");
  const [years, setYears] = useState(20);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const body = await apiPost("/api/agents/investment_agent/analyze", {
        query: "Suggest investment allocation and growth",
        params: { age: Number(age), risk_profile: risk, years: Number(years) },
      });
      setData(body);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const inv = data?.tool_results?.investment;
  const pie = inv
    ? Object.entries(inv.allocation).map(([name, value]) => ({ name, value: Number(value) * 100 }))
    : [];
  const curve = inv
    ? Array.from({ length: Number(years) }, (_, i) => ({
        year: i + 1,
        // Display corpus path roughly using annual steps from monthly SIP figure
        corpus: Number(inv.projected_corpus) * ((i + 1) / Number(years)),
      }))
    : [];

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Investment Advisor</h2>
        <p className="page-sub">Risk questionnaire → allocation and growth projection.</p>
      </header>
      <div className="filters">
        <label>Age<input type="number" value={age} onChange={(e) => setAge(e.target.value)} /></label>
        <label>
          Risk
          <select value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option value="conservative">conservative</option>
            <option value="moderate">moderate</option>
            <option value="aggressive">aggressive</option>
          </select>
        </label>
        <label>Years<input type="number" value={years} onChange={(e) => setYears(e.target.value)} /></label>
        <button className="file-btn" type="button" onClick={run} disabled={loading}>
          {loading ? "Computing…" : "Analyse"}
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
      {inv && (
        <div className="two-col">
          <section className="card" style={{ height: 280 }}>
            <h3>Allocation</h3>
            <ResponsiveContainer width="100%" height="85%">
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" outerRadius={90} label>
                  {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </section>
          <section className="card" style={{ height: 280 }}>
            <h3>Growth path (illustrative)</h3>
            <p className="muted">Projected corpus: {formatINR(inv.projected_corpus)}</p>
            <ResponsiveContainer width="100%" height="70%">
              <LineChart data={curve}>
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip formatter={(v) => formatINR(v)} />
                <Line type="monotone" dataKey="corpus" stroke="#1a73e8" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
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
