import { useCallback, useEffect, useState } from "react";
import { formatINR } from "../utils/format.js";

const CATEGORIES = [
  "rent",
  "sip_investment",
  "groceries",
  "emi",
  "travel",
  "utilities",
  "dining",
  "shopping",
  "salary",
  "transfer",
  "insurance",
  "medical",
  "entertainment",
  "education",
  "other",
];

function monthOptions(items) {
  const set = new Set();
  for (const t of items) {
    if (t.date) set.add(t.date.slice(0, 7));
  }
  return Array.from(set).sort().reverse();
}

export default function Transactions() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [month, setMonth] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [months, setMonths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingId, setSavingId] = useState(null);
  const pageSize = 50;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (month) params.set("month", month);
    if (category) params.set("category", category);
    if (search.trim()) params.set("search", search.trim());
    try {
      const r = await fetch(`/api/transactions?${params}`, { credentials: "include" });
      if (!r.ok) {
        setError("Could not load transactions.");
        setItems([]);
        return;
      }
      const body = await r.json();
      setItems(body.items || []);
      setTotal(body.total || 0);
      if (!month && !category && !search) {
        setMonths(monthOptions(body.items || []));
      }
    } catch {
      setError("Network error while loading transactions.");
    } finally {
      setLoading(false);
    }
  }, [page, month, category, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function changeCategory(txn, next) {
    if (!next || next === txn.category) return;
    setSavingId(txn.id);
    setError(null);
    try {
      const r = await fetch(`/api/transactions/${txn.id}/recategorize`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: next }),
      });
      if (!r.ok) {
        setError("Could not update category.");
        return;
      }
      const body = await r.json();
      setItems((prev) =>
        prev.map((t) => (t.id === txn.id ? body.transaction : t))
      );
    } catch {
      setError("Network error while updating category.");
    } finally {
      setSavingId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Transactions</h2>
        <p className="page-sub">
          Auto-categorised from your statements. Correct a category once and it
          sticks for matching narrations.
        </p>
      </header>

      <div className="filters">
        <label>
          Month
          <select value={month} onChange={(e) => { setPage(1); setMonth(e.target.value); }}>
            <option value="">All</option>
            {months.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={category} onChange={(e) => { setPage(1); setCategory(e.target.value); }}>
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="filter-search">
          Search
          <input
            type="search"
            value={search}
            placeholder="Narration…"
            onChange={(e) => { setPage(1); setSearch(e.target.value); }}
          />
        </label>
      </div>

      {error && <div className="banner error">{error}</div>}

      {loading && <p className="muted">Loading transactions…</p>}

      {!loading && items.length === 0 && (
        <p className="muted empty-hint">
          No transactions yet. Upload a statement on Data &amp; Profile.
        </p>
      )}

      {!loading && items.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="txn-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Direction</th>
                  <th>Amount</th>
                  <th>Category</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr key={t.id}>
                    <td>{t.date}</td>
                    <td className="txn-desc">{t.description}</td>
                    <td>
                      <span className={`chip direction ${t.direction}`}>
                        {t.direction}
                      </span>
                    </td>
                    <td className="txn-amt">{formatINR(t.amount)}</td>
                    <td>
                      <select
                        className="chip-select"
                        value={t.category || "other"}
                        disabled={savingId === t.id}
                        onChange={(e) => changeCategory(t, e.target.value)}
                      >
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span className="muted">
              Page {page} of {totalPages} · {total} rows
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
