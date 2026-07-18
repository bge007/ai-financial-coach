import { useEffect, useState } from "react";
import {
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
import { apiGet, apiPost } from "../api/client.js";
import { CHART_PALETTE, COLORS } from "../theme.js";
import { formatINR } from "../utils/format.js";

function pct(fraction) {
  return `${(Number(fraction) * 100).toFixed(0)}%`;
}

function formatAxisINR(value) {
  const n = Number(value) || 0;
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`;
  if (Math.abs(n) >= 1e3) return `₹${(n / 1e3).toFixed(0)}k`;
  return `₹${n}`;
}

function buildInvestmentNotes(inv, surplus) {
  if (!inv) return null;
  const alloc = inv.allocation || {};
  const equity = pct(alloc.equity ?? 0);
  const debt = pct(alloc.debt ?? 0);
  const cash = pct(alloc.cash ?? 0);
  const returnPct = (Number(inv.expected_return) * 100).toFixed(1);
  const blendedPct = (Number(inv.blended_return) * 100).toFixed(1);
  const lines = [
    "In simple words:",
    "",
    `Your monthly SIP of ${formatINR(inv.monthly_sip)} over ${inv.years} years, ` +
      `starting from ${formatINR(inv.starting_corpus)}, projects to about ${formatINR(inv.projected_corpus)}.`,
    "",
    `For a ${inv.risk_profile || "moderate"} profile at age ${inv.age}, the suggested mix is ` +
      `${equity} equity, ${debt} debt, and ${cash} cash.`,
    `That mix implies about ${blendedPct}% blended return; this run uses ${returnPct}% expected return.`,
  ];

  const sip = Number(inv.monthly_sip) || 0;
  const sur = surplus == null ? null : Number(surplus);
  if (sur != null && !Number.isNaN(sur)) {
    lines.push("");
    if (sur < sip) {
      lines.push(
        `Right now your estimated monthly surplus is ${formatINR(sur)}, which is below this SIP. ` +
          "Trim wants or lower the SIP until savings are steady."
      );
    } else {
      lines.push(
        `Your estimated monthly surplus is ${formatINR(sur)}, so this SIP looks affordable on paper. ` +
          "Keep an emergency buffer before raising SIPs further."
      );
    }
  }

  lines.push("");
  lines.push(
    "Bottom line: treat the projected corpus as a planning number from the finance engines, not a guarantee."
  );
  return lines.join("\n");
}

export default function InvestmentAdvisor() {
  const [monthlySip, setMonthlySip] = useState("15000");
  const [startingCorpus, setStartingCorpus] = useState("100000");
  const [expectedReturn, setExpectedReturn] = useState("11");
  const [years, setYears] = useState("20");
  const [age, setAge] = useState("30");
  const [risk, setRisk] = useState("moderate");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [profileLoaded, setProfileLoaded] = useState(false);

  useEffect(() => {
    apiGet("/api/user-profile")
      .then((body) => {
        if (!body) return;
        if (body.age != null) setAge(String(body.age));
        if (body.risk_profile) setRisk(body.risk_profile);
        if (body.monthly_income != null) {
          // Default SIP hint ~20% of declared income when surplus unknown.
          const hint = Math.max(5000, Math.round(Number(body.monthly_income) * 0.2));
          setMonthlySip(String(hint));
        }
        if (body.emergency_fund != null) {
          setStartingCorpus(String(body.emergency_fund));
        }
      })
      .catch(() => {})
      .finally(() => setProfileLoaded(true));
  }, []);

  async function run(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = await apiPost("/api/agents/investment_agent/analyze", {
        query: "Project SIP corpus and suggest allocation",
        params: {
          monthly_sip: Number(monthlySip) || 0,
          starting_corpus: Number(startingCorpus) || 0,
          expected_return: Number(expectedReturn) || 0,
          years: Number(years) || 1,
          age: Number(age) || 30,
          risk_profile: risk,
        },
      });
      setData(body);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const inv = data?.tool_results?.investment;
  const surplus = data?.tool_results?.profile?.surplus;
  const engineNotes = buildInvestmentNotes(inv, surplus);
  const coachSummary = data?.answer?.summary || "";
  const showCoach =
    Boolean(coachSummary) && !coachSummary.includes("[amount withheld]");

  const pie = inv
    ? Object.entries(inv.allocation).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value: Number(value) * 100,
      }))
    : [];
  const curve = inv
    ? Array.from({ length: Number(inv.years) || Number(years) || 1 }, (_, i) => {
        const y = i + 1;
        const totalYears = Number(inv.years) || Number(years) || 1;
        // Illustrative path toward final engine corpus (engine is source of truth for end value).
        return {
          year: y,
          corpus: Number(inv.projected_corpus) * (y / totalYears),
        };
      })
    : [];

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra</p>
        <h2>Investment Advisor</h2>
        <p className="page-sub">
          Project a long-term SIP corpus with explicit, editable assumptions.
        </p>
      </header>

      <div className="advisor-layout">
        <section className="card advisor-form-card">
          <div className="advisor-form-head">
            <div className="advisor-icon" aria-hidden="true">₹</div>
            <div>
              <h3>Investment Advisor</h3>
              <p className="step-sub" style={{ marginBottom: 0 }}>
                Project a long-term SIP corpus with explicit, editable assumptions.
              </p>
            </div>
          </div>

          <form className="advisor-form" onSubmit={run}>
            <label className="field">
              <span>Monthly SIP</span>
              <input
                type="number"
                min="0"
                step="100"
                value={monthlySip}
                onChange={(e) => setMonthlySip(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Starting corpus</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={startingCorpus}
                onChange={(e) => setStartingCorpus(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Expected return %</span>
              <input
                type="number"
                min="0"
                max="30"
                step="0.1"
                value={expectedReturn}
                onChange={(e) => setExpectedReturn(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Years</span>
              <input
                type="number"
                min="1"
                max="50"
                value={years}
                onChange={(e) => setYears(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Age</span>
              <input
                type="number"
                min="18"
                max="100"
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Risk profile</span>
              <select value={risk} onChange={(e) => setRisk(e.target.value)}>
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </label>

            <button className="primary-btn advisor-run-btn" type="submit" disabled={loading}>
              {loading ? "Running…" : "Run analysis"}
            </button>
          </form>
          {!profileLoaded && <p className="muted">Loading saved profile defaults…</p>}
        </section>

        <section className="card advisor-output-card">
          <p className="step-label">Auditable result</p>
          <h3>Analysis output</h3>

          {error && <div className="banner error">{error}</div>}

          {!inv && !error && (
            <div className="advisor-empty">
              Enter assumptions and run the analysis. Results are computed by
              deterministic Python tools.
            </div>
          )}

          {inv && (
            <div className="advisor-results">
              <div className="profile-grid">
                <div className="metric">
                  <span className="metric-label">Projected corpus</span>
                  <span className="metric-value">{formatINR(inv.projected_corpus)}</span>
                  <span className="metric-note">
                    {inv.years}y · SIP {formatINR(inv.monthly_sip)} · start{" "}
                    {formatINR(inv.starting_corpus)}
                  </span>
                </div>
                <div className="metric">
                  <span className="metric-label">Expected return</span>
                  <span className="metric-value">
                    {(Number(inv.expected_return) * 100).toFixed(2)}%
                  </span>
                  <span className="metric-note">
                    Blended from risk profile: {(Number(inv.blended_return) * 100).toFixed(2)}%
                  </span>
                </div>
              </div>

              <div className="two-col" style={{ marginTop: "1rem" }}>
                <div className="advisor-chart-block">
                  <h4>Allocation</h4>
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={pie}
                          dataKey="value"
                          nameKey="name"
                          outerRadius={80}
                          label={({ name, value }) => `${name} ${Number(value).toFixed(0)}%`}
                        >
                          {pie.map((_, i) => (
                            <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="advisor-chart-block">
                  <h4>Growth path</h4>
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={curve}>
                        <XAxis dataKey="year" />
                        <YAxis width={56} tickFormatter={formatAxisINR} />
                        <Tooltip formatter={(v) => formatINR(v)} />
                        <Line
                          type="monotone"
                          dataKey="corpus"
                          stroke={COLORS.primary}
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {engineNotes && (
                <div className="advisor-notes">
                  <h4>Result description</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{engineNotes}</p>
                </div>
              )}

              {showCoach && (
                <div className="advisor-notes" style={{ marginTop: "0.85rem" }}>
                  <h4>Coach notes</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{coachSummary}</p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
