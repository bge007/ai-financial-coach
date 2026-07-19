function Shimmer({ className = "", style }) {
  return <span className={`shimmer-block ${className}`.trim()} style={style} aria-hidden="true" />;
}

export default function PortfolioOptimizerSkeleton() {
  return (
    <div className="data-page portfolio-skeleton" aria-busy="true" aria-label="Loading portfolio analysis">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra</p>
        <h2>Portfolio Optimizer</h2>
        <p className="page-sub">
          Mean-variance optimisation on sample Indian asset returns (equity / debt / gold / cash).
          Figures are engine-computed — informational only.
        </p>
      </header>

      <div className="page-loading-status">
        <span className="page-spinner" aria-hidden="true" />
        <span>Optimising portfolio…</span>
      </div>

      <div className="profile-grid">
        {[1, 2, 3].map((i) => (
          <div className="metric skeleton-card" key={i}>
            <Shimmer className="sk-line sk-label" />
            <Shimmer className="sk-line sk-value" />
            <Shimmer className="sk-line sk-note" />
          </div>
        ))}
      </div>

      <div className="two-col portfolio-skeleton-charts">
        {[1, 2].map((i) => (
          <section className="card skeleton-card" key={i}>
            <Shimmer className="sk-line sk-title" />
            <Shimmer className="sk-chart" />
          </section>
        ))}
      </div>

      <section className="card skeleton-card">
        <Shimmer className="sk-line sk-title" />
        <Shimmer className="sk-line sk-body" />
        <Shimmer className="sk-line sk-body short" />
        <Shimmer className="sk-line sk-body" style={{ width: "72%" }} />
      </section>
    </div>
  );
}
