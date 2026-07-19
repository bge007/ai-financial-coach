import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export default function ConsultationChatWidget({
  open,
  booking,
  minimized,
  onMinimizedChange,
  messages,
  chatInput,
  onChatInput,
  onSend,
  chatLoading,
  chatWarning,
  onExit,
  exiting,
  chatEndRef,
}) {
  const [showExitPanel, setShowExitPanel] = useState(false);
  const [rating, setRating] = useState(null);

  useEffect(() => {
    if (!open) {
      setShowExitPanel(false);
      setRating(null);
    }
  }, [open]);

  if (!open || !booking) return null;

  function handleExitClick() {
    setShowExitPanel(true);
  }

  function handleConfirmExit() {
    onExit(rating);
  }

  const header = (
    <div
      className="consultation-chat-widget-header"
      onClick={minimized ? () => onMinimizedChange(false) : undefined}
      onKeyDown={
        minimized
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onMinimizedChange(false);
            }
          : undefined
      }
      role={minimized ? "button" : undefined}
      tabIndex={minimized ? 0 : undefined}
    >
      <div className="consultation-chat-widget-title">
        {!minimized && <strong>Expert consultation</strong>}
        <span className="consultation-chat-topic-chip">{booking.topic_label}</span>
      </div>
      {!minimized && (
        <div className="consultation-chat-widget-actions">
          <button
            type="button"
            className="consultation-chat-icon-btn"
            onClick={() => onMinimizedChange(true)}
            aria-label="Minimize chat"
            title="Minimize"
          >
            −
          </button>
          <button
            type="button"
            className="consultation-chat-exit-btn"
            onClick={handleExitClick}
            disabled={exiting}
          >
            Exit
          </button>
        </div>
      )}
      {minimized && (
        <span className="muted" style={{ fontSize: "0.75rem" }}>
          Tap to open
        </span>
      )}
    </div>
  );

  return createPortal(
    <div
      className={`consultation-chat-widget${minimized ? " minimized" : ""}`}
      role="dialog"
      aria-label="Expert consultation chat"
    >
      {header}

      {!minimized && (
        <div className="consultation-chat-body">
          {chatWarning && <div className="banner warn">{chatWarning}</div>}
          <div className="premium-chat-messages">
            {messages.map((msg, idx) => (
              <div
                key={`${msg.role}-${idx}`}
                className={
                  msg.role === "user"
                    ? "premium-chat-bubble user"
                    : "premium-chat-bubble expert"
                }
              >
                {msg.text}
              </div>
            ))}
            {chatLoading && (
              <div className="premium-chat-bubble expert muted">Thinking…</div>
            )}
            <div ref={chatEndRef} />
          </div>

          {!showExitPanel ? (
            <div className="premium-chat-compose">
              <textarea
                rows={2}
                value={chatInput}
                onChange={(e) => onChatInput(e.target.value)}
                placeholder="Ask your finance expert…"
                disabled={chatLoading || exiting}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    onSend();
                  }
                }}
              />
              <button
                type="button"
                className="primary-btn"
                onClick={onSend}
                disabled={chatLoading || exiting || !chatInput.trim()}
              >
                {chatLoading ? "…" : "Send"}
              </button>
            </div>
          ) : (
            <div className="consultation-chat-exit-panel">
              <strong>Rate your expert</strong>
              <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                Optional — then exit to book a new session.
              </p>
              <div className="consultation-exit-rating" role="group" aria-label="Expert rating">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={rating === n ? "selected" : ""}
                    onClick={() => setRating(n)}
                    aria-label={`${n} star${n > 1 ? "s" : ""}`}
                    aria-pressed={rating === n}
                  >
                    ★
                  </button>
                ))}
              </div>
              <div className="consultation-chat-exit-actions">
                <button
                  type="button"
                  className="primary-btn"
                  onClick={handleConfirmExit}
                  disabled={exiting}
                >
                  {exiting ? "Closing…" : "Submit & exit"}
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => setShowExitPanel(false)}
                  disabled={exiting}
                >
                  Back to chat
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>,
    document.body
  );
}
