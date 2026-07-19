import { useState } from "react";
import { askStream } from "../api/client.js";

export default function Coach() {
  const [query, setQuery] = useState("Should I prepay my loan or invest the surplus?");
  const [text, setText] = useState("");
  const [meta, setMeta] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function send() {
    setLoading(true);
    setError(null);
    setText("");
    setAnswer(null);
    setMeta(null);
    await askStream(query, {
      onMeta: setMeta,
      onToken: (t) => setText((prev) => prev + t),
      onDone: (a) => {
        setAnswer(a);
        setLoading(false);
      },
      onError: (e) => {
        setError(e.message);
        setLoading(false);
      },
    });
    setLoading(false);
  }

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra · Ask the Coach</p>
        <h2>Ask the Coach</h2>
        <p className="page-sub">Grounded answers with citations and an agent-route badge.</p>
      </header>
      <div className="coach-compose">
        <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={3} />
        <button className="primary-btn" type="button" onClick={send} disabled={loading || !query.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
      {meta?.llm_warning && <div className="banner warn">{meta.llm_warning}</div>}
      {meta && (
        <div className="route-badges">
          {(meta.route || []).map((r) => (
            <span className="chip" key={r}>{r}</span>
          ))}
        </div>
      )}
      {(text || answer) && (
        <section className="card">
          <h3>Answer</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{answer?.summary || text}</p>
        </section>
      )}
      {meta?.citations?.length > 0 && (
        <section className="card">
          <h3>Sources</h3>
          <ul className="summary-list">
            {meta.citations.map((c, i) => (
              <li key={`${c.source_file}-${i}`}>
                <span>{c.source_file} · p.{c.page}</span>
                <strong>{Number(c.score).toFixed(3)}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
