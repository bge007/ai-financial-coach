import { useState } from "react";
import { apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

export default function TaxRetirement() {
  const [gross, setGross] = useState(1200000);
  const [c80, setC80] = useState(150000);
  const [d80, setD80] = useState(25000);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const body = await apiPost("/api/agents/tax_agent/analyze", {
        query: "Compare old vs new tax regime and retirement projections",
        params: {
          gross_income: Number(gross),
          deductions: { "80c": Number(c80), "80d": Number(d80) },
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

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Tax &amp; Retirement</h2>
        <p className="page-sub">Old vs new regime comparison with SIP / EPF / NPS cards.</p>
      </header>
      <div className="filters">
        <label>Gross income<input type="number" value={gross} onChange={(e) => setGross(e.target.value)} /></label>
        <label>80C<input type="number" value={c80} onChange={(e) => setC80(e.target.value)} /></label>
        <label>80D<input type="number" value={d80} onChange={(e) => setD80(e.target.value)} /></label>
        <button className="file-btn" type="button" onClick={run} disabled={loading}>
          {loading ? "Computing…" : "Compare"}
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
      {tax && (
        <>
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
              <span className="metric-note">FY {tax.financial_year}</span>
            </div>
          </div>
          <div className="profile-grid">
            <div className="metric">
              <span className="metric-label">SIP 10y (₹10k/mo @12%)</span>
              <span className="metric-value">{formatINR(tax.sip_10y)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">EPF 10y</span>
              <span className="metric-value">{formatINR(tax.epf_corpus)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">NPS 10y</span>
              <span className="metric-value">{formatINR(tax.nps_corpus)}</span>
            </div>
          </div>
        </>
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
