import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiPost } from "../api/client.js";
import PortfolioOptimizerSkeleton from "../components/PortfolioOptimizerSkeleton.jsx";
import { CHART_PALETTE, COLORS } from "../theme.js";
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

  if (loading) return <PortfolioOptimizerSkeleton />;
  if (error) return <div className="banner error">{error}</div>;

  const portfolio = data?.tool_results?.portfolio;
  const portfolioError = data?.tool_results?.portfolio_error;
  const sharpeWeights = portfolio
    ? Object.entries(portfolio.max_sharpe.weights).map(([name, value]) => ({
        name,
        value: Number(value) * 100,
      }))
    : [];
  const frontier = (portfolio?.frontier || []).map((p) => ({
    volatility: Number(p.volatility) * 100,
    ret: Number(p.return) * 100,
    sharpe: Number(p.sharpe),
  }));

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra</p>
        <h2>Portfolio Optimizer</h2>
        <p className="page-sub">
          Mean-variance optimisation on sample Indian asset returns (equity / debt / gold / cash).
          Figures are engine-computed — informational only.
        </p>
      </header>

      {!portfolio ? (
        <p className="muted empty-hint">
          {portfolioError
            ? `Could not compute portfolio weights: ${portfolioError}`
            : "Could not compute portfolio weights yet. Retry in a moment."}
        </p>
      ) : (
        <>
          <div className="profile-grid">
            <div className="metric">
              <span className="metric-label">Max Sharpe</span>
              <span className="metric-value">{Number(portfolio.max_sharpe.sharpe).toFixed(2)}</span>
              <span className="metric-note">
                Return {(Number(portfolio.max_sharpe.expected_return) * 100).toFixed(1)}% · Vol{" "}
                {(Number(portfolio.max_sharpe.volatility) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Min volatility Sharpe</span>
              <span className="metric-value">{Number(portfolio.min_volatility.sharpe).toFixed(2)}</span>
              <span className="metric-note">
                Return {(Number(portfolio.min_volatility.expected_return) * 100).toFixed(1)}% · Vol{" "}
                {(Number(portfolio.min_volatility.volatility) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">15y corpus @ {formatINR(portfolio.monthly_sip)} SIP</span>
              <span className="metric-value">{formatINR(portfolio.corpus_15y)}</span>
            </div>
          </div>

          <div className="two-col" style={{ marginTop: "1.15rem" }}>
            <section className="card" style={{ height: 300 }}>
              <h3>Max-Sharpe weights</h3>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie data={sharpeWeights} dataKey="value" nameKey="name" outerRadius={90} label>
                    {sharpeWeights.map((_, i) => (
                      <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
                </PieChart>
              </ResponsiveContainer>
            </section>
            <section className="card" style={{ height: 300 }}>
              <h3>Efficient frontier</h3>
              <ResponsiveContainer width="100%" height="85%">
                <LineChart data={frontier}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="volatility" unit="%" />
                  <YAxis unit="%" />
                  <Tooltip />
                  <Line type="monotone" dataKey="ret" stroke={COLORS.primary} strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </section>
          </div>
        </>
      )}

      <section className="card">
        <h3>Coach notes</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{data?.answer?.summary || "No analysis yet."}</p>
        {(data?.answer?.recommendations || []).length > 0 && (
          <ul className="action-list">
            {data.answer.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
