import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost, consultationStream } from "../api/client.js";
import ConsultationBookingModal from "../components/ConsultationBookingModal.jsx";
import ConsultationChatWidget from "../components/ConsultationChatWidget.jsx";
import { formatINR } from "../utils/format.js";

function priorityClass(priority) {
  if (priority === "high") return "premium-priority high";
  if (priority === "low") return "premium-priority low";
  return "premium-priority medium";
}

const EMPTY_BOOKING = {
  topic: "financial_planning",
  preferred_date: "",
  preferred_time: "morning",
  contact_phone: "",
  notes: "",
};

const MONEY_MITRA_GREETING = "Hi! I'm your Money Mitra — happy to help you.";

function consultationWelcomeMessage(booking, { returning = false } = {}) {
  const { topic_label: topic, preferred_date: date, preferred_time: time } = booking;

  if (returning) {
    return (
      `${MONEY_MITRA_GREETING} Your ${topic} consultation is scheduled for ${date}. ` +
      "What would you like to discuss today?"
    );
  }

  return (
    `${MONEY_MITRA_GREETING} Your ${topic} session is booked for ${date} (${time}). ` +
    "What would you like to discuss today?"
  );
}

function ConsultationSection({ step, booking, onBookClick, onResumeChat }) {
  return (
    <section className="card premium-section premium-section-highlight">
      <div className="premium-section-head">
        <span className="premium-section-icon" aria-hidden="true">{step}</span>
        <div>
          <h3>Book 1-on-1 with a finance expert</h3>
          <p className="muted">
            Consult on financial planning, budgeting, savings, and EMIs — then chat with our
            AI expert powered by OpenRouter.
          </p>
        </div>
      </div>

      {booking && (
        <div className="premium-booking-summary">
          <span className="premium-outlook-label">Scheduled</span>
          <p>
            <strong>{booking.topic_label}</strong> · {booking.preferred_date} ·{" "}
            {booking.preferred_time}
          </p>
        </div>
      )}

      {!booking && (
        <button type="button" className="primary-btn" onClick={onBookClick}>
          Book consultation
        </button>
      )}

      {booking && (
        <button type="button" className="ghost-btn" onClick={onResumeChat} style={{ marginTop: "0.5rem" }}>
          Open expert chat
        </button>
      )}
    </section>
  );
}

export default function MyMoneyMitra() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [bookingForm, setBookingForm] = useState(EMPTY_BOOKING);
  const [booking, setBooking] = useState(null);
  const [bookingError, setBookingError] = useState(null);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMinimized, setChatMinimized] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatWarning, setChatWarning] = useState(null);
  const [exiting, setExiting] = useState(false);
  const [pendingAutoSend, setPendingAutoSend] = useState(null);
  const chatEndRef = useRef(null);

  const sendChatMessage = useCallback(
    async (rawMessage) => {
      const message = (rawMessage ?? chatInput).trim();
      if (!message || chatLoading || !booking?.id) return;

      setChatInput("");
      setChatLoading(true);
      setChatWarning(null);
      setChatMessages((prev) => [...prev, { role: "user", text: message }]);

      let assistantText = "";
      await consultationStream(
        { message, booking_id: booking.id },
        {
          onMeta: (meta) => {
            if (meta?.llm_warning) setChatWarning(meta.llm_warning);
          },
          onToken: (token) => {
            assistantText += token;
            setChatMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant" && last.streaming) {
                next[next.length - 1] = {
                  role: "assistant",
                  text: assistantText,
                  streaming: true,
                };
                return next;
              }
              return [...next, { role: "assistant", text: assistantText, streaming: true }];
            });
          },
          onDone: (payload) => {
            const finalText = payload?.reply || assistantText;
            setChatMessages((prev) => {
              const next = [...prev];
              if (next[next.length - 1]?.role === "assistant") {
                next[next.length - 1] = { role: "assistant", text: finalText };
                return next;
              }
              return [...next, { role: "assistant", text: finalText }];
            });
            setChatLoading(false);
          },
          onError: (err) => {
            setChatWarning(err.message);
            setChatLoading(false);
          },
        }
      );
      setChatLoading(false);
    },
    [booking, chatInput, chatLoading]
  );

  useEffect(() => {
    apiGet("/api/premium")
      .then((payload) => {
        setData(payload);
        if (payload?.consultation?.booking) {
          const b = payload.consultation.booking;
          setBooking(b);
          setChatOpen(true);
          setChatMinimized(true);
          setChatMessages([
            {
              role: "assistant",
              text: consultationWelcomeMessage(b, { returning: true }),
            },
          ]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatLoading]);

  useEffect(() => {
    if (pendingAutoSend && booking?.id && !chatLoading) {
      const msg = pendingAutoSend;
      setPendingAutoSend(null);
      sendChatMessage(msg);
    }
  }, [pendingAutoSend, booking, chatLoading, sendChatMessage]);

  async function exportReport() {
    setExporting(true);
    try {
      const r = await fetch("/api/report/consolidated.pdf", { credentials: "include" });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || "Could not export report.");
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().slice(0, 10);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MoneyMitra-Report-${stamp}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      window.alert(err.message || "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  async function submitBooking(e) {
    e.preventDefault();
    setBookingError(null);
    setBookingSubmitting(true);
    const notesToSend = bookingForm.notes.trim();
    try {
      const res = await apiPost("/api/premium/consultation/book", bookingForm);
      setBooking(res.booking);
      setBookingModalOpen(false);
      setChatOpen(true);
      setChatMinimized(false);
      setChatMessages([
        {
          role: "assistant",
          text: consultationWelcomeMessage(res.booking),
        },
      ]);
      if (notesToSend) {
        setPendingAutoSend(notesToSend);
      }
      setBookingForm(EMPTY_BOOKING);
    } catch (err) {
      setBookingError(err.message || "Could not book consultation.");
    } finally {
      setBookingSubmitting(false);
    }
  }

  async function handleExitConsultation(rating) {
    if (!booking?.id) return;
    setExiting(true);
    try {
      await apiPost("/api/premium/consultation/close", {
        booking_id: booking.id,
        rating: rating ?? undefined,
      });
      setBooking(null);
      setChatOpen(false);
      setChatMinimized(false);
      setChatMessages([]);
      setChatInput("");
      setChatWarning(null);
    } catch (err) {
      window.alert(err.message || "Could not close consultation.");
    } finally {
      setExiting(false);
    }
  }

  if (loading) return <p className="muted">Loading My Money Mitra…</p>;
  if (error) return <div className="banner error">{error}</div>;

  const subs = data?.subscriptions?.items || [];
  const topics = data?.consultation?.topics || [];
  const timeSlots = data?.consultation?.time_slots || [];

  return (
    <div className="data-page premium-page">
      <header className="page-header">
        <p className="page-kicker">Premium services</p>
        <h2>
          My Money Mitra
          <span className="premium-badge">Premium</span>
        </h2>
        <p className="page-sub">
          Expert consultations, detailed reports, credit-health guidance, and subscription insights.
        </p>
      </header>

      <ConsultationSection
        step={1}
        booking={booking}
        onBookClick={() => {
          setBookingError(null);
          setBookingModalOpen(true);
        }}
        onResumeChat={() => {
          setChatOpen(true);
          setChatMinimized(false);
        }}
      />

      <section className="card premium-section">
        <div className="premium-section-head">
          <span className="premium-section-icon" aria-hidden="true">2</span>
          <div>
            <h3>Detailed analysis report</h3>
            <p className="muted">
              {data?.report?.description ||
                "Download one consolidated PDF covering all MoneyMitra modules."}
            </p>
          </div>
        </div>
        {data?.report?.available ? (
          <button
            type="button"
            className="primary-btn premium-export-btn"
            onClick={exportReport}
            disabled={exporting}
          >
            {exporting ? "Generating PDF…" : "Download consolidated PDF"}
          </button>
        ) : (
          <p className="muted empty-hint">
            Upload a bank statement on Data &amp; Profile to generate your report.
          </p>
        )}
      </section>

      <section className="card premium-section">
        <div className="premium-section-head">
          <span className="premium-section-icon" aria-hidden="true">3</span>
          <div>
            <h3>CIBIL credit score tips</h3>
            <p className="muted">{data?.cibil?.disclaimer}</p>
          </div>
        </div>
        {data?.cibil?.outlook && (
          <div className="premium-outlook">
            <span className="premium-outlook-label">Outlook</span>
            <p>{data.cibil.outlook}</p>
          </div>
        )}
        <ul className="premium-tip-list">
          {(data?.cibil?.tips || []).map((tip) => (
            <li key={tip.title} className="premium-tip">
              <div className="premium-tip-head">
                <strong>{tip.title}</strong>
                <span className={priorityClass(tip.priority)}>{tip.priority}</span>
              </div>
              <p className="premium-tip-factor">{tip.factor}</p>
              <p className="premium-tip-detail">{tip.detail}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="card premium-section">
        <div className="premium-section-head">
          <span className="premium-section-icon" aria-hidden="true">4</span>
          <div>
            <h3>My subscriptions</h3>
            <p className="muted">
              Recurring OTT, telecom and digital services detected from your debits.
            </p>
          </div>
        </div>

        {subs.length === 0 ? (
          <p className="muted empty-hint">
            No recurring subscriptions found yet. Netflix, Hotstar, Jio, Airtel and similar
            charges will appear here after you upload statements.
          </p>
        ) : (
          <>
            <div className="premium-sub-total">
              <span>Estimated monthly total</span>
              <strong>{formatINR(data.subscriptions.monthly_total)}</strong>
            </div>
            <div className="table-wrap premium-table-wrap">
              <table className="premium-sub-table">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Frequency</th>
                    <th>Last paid</th>
                  </tr>
                </thead>
                <tbody>
                  {subs.map((sub) => (
                    <tr key={sub.name}>
                      <td className="sub-service">{sub.name}</td>
                      <td className="sub-category-cell">{sub.category}</td>
                      <td className="sub-amount">{formatINR(sub.amount)}</td>
                      <td className="sub-frequency">{sub.frequency}</td>
                      <td className="sub-date">{sub.last_paid}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <ConsultationBookingModal
        open={bookingModalOpen}
        onClose={() => !bookingSubmitting && setBookingModalOpen(false)}
        topics={topics}
        timeSlots={timeSlots}
        form={bookingForm}
        onChange={setBookingForm}
        onSubmit={submitBooking}
        error={bookingError}
        submitting={bookingSubmitting}
      />

      <ConsultationChatWidget
        open={chatOpen}
        booking={booking}
        minimized={chatMinimized}
        onMinimizedChange={setChatMinimized}
        messages={chatMessages}
        chatInput={chatInput}
        onChatInput={setChatInput}
        onSend={() => sendChatMessage()}
        chatLoading={chatLoading}
        chatWarning={chatWarning}
        onExit={handleExitConsultation}
        exiting={exiting}
        chatEndRef={chatEndRef}
      />
    </div>
  );
}
