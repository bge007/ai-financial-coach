import GlassModal from "./GlassModal.jsx";

export default function ConsultationBookingModal({
  open,
  onClose,
  topics,
  timeSlots,
  form,
  onChange,
  onSubmit,
  error,
  submitting,
}) {
  return (
    <GlassModal
      open={open}
      onClose={onClose}
      titleId="consultation-modal-title"
      size="consultation"
    >
      <button type="button" className="glass-modal-close" onClick={onClose} aria-label="Close">
        ×
      </button>

      <div className="consultation-modal-head">
        <p className="page-kicker">Premium · Expert session</p>
        <h2 id="consultation-modal-title">Book 1-on-1 consultation</h2>
        <p className="muted">
          Financial planning, budgeting, savings &amp; EMIs — then chat with our AI expert.
        </p>
      </div>

      <form className="premium-booking-form consultation-modal-form" onSubmit={onSubmit}>
        <label className="field">
          <span>Topic</span>
          <select
            value={form.topic}
            onChange={(e) => onChange({ ...form, topic: e.target.value })}
            required
          >
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Preferred date</span>
          <input
            type="date"
            value={form.preferred_date}
            min={new Date().toISOString().slice(0, 10)}
            onChange={(e) => onChange({ ...form, preferred_date: e.target.value })}
            required
          />
        </label>
        <label className="field">
          <span>Time slot</span>
          <select
            value={form.preferred_time}
            onChange={(e) => onChange({ ...form, preferred_time: e.target.value })}
            required
          >
            {timeSlots.map((slot) => (
              <option key={slot.id} value={slot.id}>
                {slot.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Phone (optional)</span>
          <input
            type="tel"
            value={form.contact_phone}
            onChange={(e) => onChange({ ...form, contact_phone: e.target.value })}
            placeholder="+91 …"
          />
        </label>
        <label className="field premium-booking-notes">
          <span>What would you like to discuss?</span>
          <textarea
            rows={3}
            value={form.notes}
            onChange={(e) => onChange({ ...form, notes: e.target.value })}
            placeholder="e.g. reduce dining spend, plan SIP, manage EMIs…"
          />
        </label>
        {error && <div className="banner error">{error}</div>}
        <div className="premium-booking-actions consultation-modal-actions">
          <button type="submit" className="primary-btn" disabled={submitting}>
            {submitting ? "Booking…" : "Confirm & open expert chat"}
          </button>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </GlassModal>
  );
}
