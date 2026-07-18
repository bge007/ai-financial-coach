import { useEffect, useState } from "react";
import { apiPost } from "../api/client.js";
import { formatINR } from "../utils/format.js";

export default function PortfolioOptimizer() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiPost("/api/agents/portfolio_agent/analyze", {
      query: "Optimise my portfolio sharpe and frontier",
      params: {},
    })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Optimising…</p>;
  if (error) return <div className="banner error">{error}</div>;

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Portfolio Optimizer</h2>
        <p className="page-sub">Mean-variance view via the portfolio agent (engine-backed when returns data is supplied).</p>
      </header>
      <section className="card">
        <h3>Coach notes</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{data?.answer?.summary || "No analysis yet."}</p>
        {(data?.answer?.recommendations || []).length > 0 && (
          <ul>
            {data.answer.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </section>
      {data?.tool_results?.profile && (
        <section className="card">
          <h3>Profile anchors</h3>
          <p>Surplus: {formatINR(data.tool_results.profile.surplus)}</p>
        </section>
      )}
    </div>
  );
}
