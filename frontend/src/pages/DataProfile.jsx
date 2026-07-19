import { useCallback, useEffect, useRef, useState } from "react";
import { formatINR } from "../utils/format.js";

const ACCEPT = ".csv,.pdf,text/csv,application/pdf";

const EMPTY_FORM = {
  name: "",
  age: "",
  city: "",
  monthly_income: "",
  emergency_fund: "",
  risk_profile: "moderate",
};

export default function DataProfile() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState(null);

  const [computed, setComputed] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadMsg, setUploadMsg] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  const loadAll = useCallback(async () => {
    setLoadingProfile(true);
    setError(null);
    try {
      const [userRes, finRes] = await Promise.all([
        fetch("/api/user-profile", { credentials: "include" }),
        fetch("/api/profile", { credentials: "include" }),
      ]);
      if (userRes.status === 401 || finRes.status === 401) {
        setError("Session expired — please log in again.");
        return;
      }
      if (userRes.ok) {
        const body = await userRes.json();
        if (body) {
          setForm({
            name: body.name || "",
            age: body.age != null ? String(body.age) : "",
            city: body.city || "",
            monthly_income:
              body.monthly_income != null ? String(body.monthly_income) : "",
            emergency_fund:
              body.emergency_fund != null ? String(body.emergency_fund) : "",
            risk_profile: body.risk_profile || "moderate",
          });
        }
      }
      if (finRes.ok) {
        setComputed(await finRes.json());
      }
    } catch {
      setError("Network error while loading profile.");
    } finally {
      setLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setSavedMsg(null);
  }

  async function saveProfile(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedMsg(null);
    try {
      const payload = {
        name: form.name.trim(),
        age: form.age === "" ? null : Number(form.age),
        city: form.city.trim(),
        monthly_income:
          form.monthly_income === "" ? null : form.monthly_income,
        emergency_fund:
          form.emergency_fund === "" ? null : form.emergency_fund,
        risk_profile: form.risk_profile,
      };
      const r = await fetch("/api/user-profile", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail = body.detail;
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => d.msg).join("; ")
              : "Could not save profile."
        );
        return;
      }
      setSavedMsg("Profile saved.");
      setForm({
        name: body.name || "",
        age: body.age != null ? String(body.age) : "",
        city: body.city || "",
        monthly_income:
          body.monthly_income != null ? String(body.monthly_income) : "",
        emergency_fund:
          body.emergency_fund != null ? String(body.emergency_fund) : "",
        risk_profile: body.risk_profile || "moderate",
      });
    } catch {
      setError("Network error while saving profile.");
    } finally {
      setSaving(false);
    }
  }

  async function uploadFile(file) {
    if (!file) return;

    const ext = file.name.toLowerCase().split(".").pop();
    if (ext !== "csv" && ext !== "pdf") {
      setError("Only CSV and PDF bank statements are supported.");
      setUploadMsg(null);
      return;
    }

    setUploading(true);
    setError(null);
    setUploadMsg(null);
    setSummary(null);
    try {
      const data = new FormData();
      data.append("file", file);
      const r = await fetch("/api/upload", {
        method: "POST",
        credentials: "include",
        body: data,
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (r.status === 401) {
          setError("Session expired — please log in again.");
          return;
        }
        const detail = body.detail;
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
              : "Upload failed."
        );
        return;
      }
      setSummary(body.summary);
      setComputed(body.profile);
      if (body.summary?.duplicate) {
        setUploadMsg("This file was already uploaded — showing existing data.");
      } else {
        setUploadMsg(
          `Uploaded ${body.summary?.rows_parsed ?? 0} transactions from ${body.summary?.filename ?? file.name}.`
        );
      }
    } catch {
      setError("Network error during upload.");
    } finally {
      setUploading(false);
    }
  }

  function onChooseFileClick() {
    fileInputRef.current?.click();
  }

  function onFileInput(e) {
    const file = e.target.files?.[0];
    uploadFile(file);
    e.target.value = "";
  }

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    uploadFile(file);
  }

  async function deleteAllData() {
    setDeleting(true);
    setError(null);
    try {
      const r = await fetch("/api/me/data", {
        method: "DELETE",
        credentials: "include",
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(body.detail || "Could not delete your data.");
        return;
      }
      setConfirmDelete(false);
      setSummary(null);
      setComputed(null);
      setForm(EMPTY_FORM);
      setSavedMsg("All financial data deleted.");
    } catch {
      setError("Network error while deleting data.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="data-page">
      <header className="page-header">
        <p className="page-kicker">MoneyMitra · Your trust, our guidance</p>
        <h2>Data &amp; Profile</h2>
        <p className="page-sub">
          Complete your profile, then upload a statement. Declared inputs ground
          projections; statement figures are computed in Python — never by the LLM.
        </p>
      </header>

      {error && <div className="banner error">{error}</div>}
      {savedMsg && <div className="banner ok">{savedMsg}</div>}
      {uploadMsg && <div className="banner ok">{uploadMsg}</div>}

      <div className="profile-steps">
        <section className="step-card">
          <p className="step-label">Step 1</p>
          <h3>Complete your profile</h3>
          <p className="step-sub">These verified inputs ground every projection.</p>

          <form className="profile-form" onSubmit={saveProfile}>
            <label className="field">
              <span>Name</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </label>
            <label className="field">
              <span>Age</span>
              <input
                type="number"
                min="18"
                max="100"
                value={form.age}
                onChange={(e) => updateField("age", e.target.value)}
                placeholder="e.g. 32"
              />
            </label>
            <label className="field">
              <span>City</span>
              <input
                type="text"
                value={form.city}
                onChange={(e) => updateField("city", e.target.value)}
                placeholder="e.g. Bengaluru"
                autoComplete="address-level2"
              />
            </label>
            <label className="field">
              <span>Monthly income</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.monthly_income}
                onChange={(e) => updateField("monthly_income", e.target.value)}
                placeholder="₹"
              />
            </label>
            <label className="field">
              <span>Emergency fund</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.emergency_fund}
                onChange={(e) => updateField("emergency_fund", e.target.value)}
                placeholder="₹"
              />
            </label>
            <label className="field">
              <span>Risk profile</span>
              <select
                value={form.risk_profile}
                onChange={(e) => updateField("risk_profile", e.target.value)}
              >
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </label>

            <button className="primary-btn" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save profile"}
            </button>
          </form>
        </section>

        <section
          className={`step-card upload-card ${dragOver ? "drag-over" : ""} ${uploading ? "busy" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <p className="step-label">Step 2</p>
          <div className="upload-icon" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <path
                d="M7 18a5 5 0 0 1-.5-9.97A6.5 6.5 0 0 1 18.8 10H19a4 4 0 0 1 0 8h-1"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path
                d="M12 16V8m0 0l-3 3m3-3l3 3"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h3>Upload a bank statement</h3>
          <p className="step-sub">
            Indian bank CSV or text-based PDF, up to 10 MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            onChange={onFileInput}
            disabled={uploading}
            className="file-input-hidden"
            aria-hidden="true"
            tabIndex={-1}
          />
          <button
            type="button"
            className="primary-btn file-btn-inline"
            onClick={onChooseFileClick}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Choose file"}
          </button>
        </section>
      </div>

      {summary && (
        <section className="card">
          <h3>Parse summary</h3>
          {summary.duplicate ? (
            <p className="muted">
              Duplicate file detected — no new rows were added.
            </p>
          ) : (
            <ul className="summary-list">
              <li>
                <span>File</span>
                <strong>{summary.filename}</strong>
              </li>
              <li>
                <span>Rows parsed</span>
                <strong>{summary.rows_parsed}</strong>
              </li>
              <li>
                <span>Rows skipped</span>
                <strong>{summary.rows_skipped}</strong>
              </li>
              <li>
                <span>Date range</span>
                <strong>
                  {summary.date_range_start && summary.date_range_end
                    ? `${summary.date_range_start} → ${summary.date_range_end}`
                    : "—"}
                </strong>
              </li>
            </ul>
          )}
        </section>
      )}

      <section className="card">
        <h3>Computed from statements</h3>
        {loadingProfile && <p className="muted">Loading…</p>}
        {!loadingProfile && !computed && (
          <p className="muted empty-hint">
            No statement-derived profile yet. Upload a bank file in Step 2 to
            compute income, expenses, surplus, and EMI outgo.
          </p>
        )}
        {computed && (
          <div className="profile-grid">
            <div className="metric">
              <span className="metric-label">Monthly income</span>
              <span className="metric-value">{formatINR(computed.monthly_income)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Monthly expenses</span>
              <span className="metric-value">{formatINR(computed.monthly_expenses)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Surplus</span>
              <span className="metric-value">{formatINR(computed.surplus)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">EMI outgo</span>
              <span className="metric-value">{formatINR(computed.emi_outgo)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Total debt</span>
              <span className="metric-value">{formatINR(computed.total_debt)}</span>
              <span className="metric-note">
                0 when statements omit outstanding principal
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="card privacy-card">
        <p className="step-label">Privacy</p>
        <h3>Delete financial data</h3>
        <p className="step-sub">
          Permanently removes your SQLite records, uploaded sources and Qdrant
          vectors.
        </p>
        <button
          type="button"
          className="outline-danger-btn"
          onClick={() => setConfirmDelete(true)}
        >
          Delete all my data
        </button>
      </section>

      {confirmDelete && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => !deleting && setConfirmDelete(false)}
        >
          <div
            className="modal-card glass"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-title"
            aria-describedby="delete-desc"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="step-label">Confirm</p>
            <h3 id="delete-title">Permanently delete all data?</h3>
            <p id="delete-desc" className="step-sub">
              This cannot be undone. Your transactions, uploads, computed
              profile, preferences and vector index for this account will be
              removed.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-btn"
                disabled={deleting}
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="primary-btn"
                disabled={deleting}
                onClick={deleteAllData}
              >
                {deleting ? "Deleting…" : "Delete all my data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
