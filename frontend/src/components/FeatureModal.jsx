import GlassModal from "./GlassModal.jsx";

export default function FeatureModal({ feature, onClose, onGetStarted }) {
  if (!feature) return null;

  return (
    <GlassModal open={Boolean(feature)} onClose={onClose} titleId="feature-modal-title" size="feature">
      <button type="button" className="glass-modal-close" onClick={onClose} aria-label="Close">
        ×
      </button>

      <div className="feature-modal-head">
        <span className="feature-modal-icon" aria-hidden="true">
          {feature.icon}
        </span>
        <div>
          <p className="page-kicker">MoneyMitra feature</p>
          <h2 id="feature-modal-title">{feature.title}</h2>
        </div>
      </div>

      <p className="feature-modal-blurb">{feature.blurb}</p>

      <ul className="feature-modal-list">
        {feature.details.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <div className="feature-modal-actions">
        <button type="button" className="primary-btn" onClick={onGetStarted}>
          Get started free
        </button>
        <button type="button" className="ghost-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </GlassModal>
  );
}
