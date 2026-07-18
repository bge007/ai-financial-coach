import { useCallback, useEffect, useState } from "react";
import { formatINR } from "../utils/format.js";

const ACCEPT = ".csv,.pdf,text/csv,application/pdf";

export default function DataProfile() {
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoadingProfile(true);
    setError(null);
    try {
      const r = await fetch("/api/profile", { credentials: "include" });
      if (r.status === 401) {
        setError("Session expired — please log in again.");
        setProfile(null);
        return;
      }
      if (!r.ok) {
        setError("Could not load your financial profile.");
        return;
      }
      const body = await r.json();
      setProfile(body);
    } catch {
      setError("Network error while loading profile.");
    } finally {
      setLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  async function uploadFile(file) {
    if (!file) return;
    setUploading(true);
    setError(null);
    setSummary(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await fetch("/api/upload", {
        method: "POST",
        credentials: "include",
        body: form,
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(body.detail || "Upload failed.");
        return;
      }
      setSummary(body.summary);
      setProfile(body.profile);
    } catch {
      setError("Network error during upload.");
    } finally {
      setUploading(false);
    }
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

  return (
    <div className="data-page">
      <header className="page-header">
        <h2>Data &amp; Profile</h2>
        <p className="page-sub">
          Upload a bank CSV or PDF statement. We parse transactions and derive
          your financial profile — every rupee figure is computed in Python, not
          by the LLM.
        </p>
      </header>

      <section
        className={`dropzone ${dragOver ? "drag-over" : ""} ${uploading ? "busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <p className="dropzone-title">
          {uploading ? "Uploading & parsing…" : "Drop a CSV or PDF here"}
        </p>
        <p className="dropzone-hint">Max 10 MB · HDFC / ICICI / SBI style layouts</p>
        <label className="file-btn">
          Choose file
          <input
            type="file"
            accept={ACCEPT}
            onChange={onFileInput}
            disabled={uploading}
            hidden
          />
        </label>
      </section>

      {error && <div className="banner error">{error}</div>}

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
        <h3>Financial profile</h3>
        {loadingProfile && <p className="muted">Loading profile…</p>}
        {!loadingProfile && !profile && (
          <p className="muted empty-hint">
            No profile yet. Upload a statement to compute income, expenses,
            surplus, and EMI outgo.
          </p>
        )}
        {profile && (
          <div className="profile-grid">
            <div className="metric">
              <span className="metric-label">Monthly income</span>
              <span className="metric-value">{formatINR(profile.monthly_income)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Monthly expenses</span>
              <span className="metric-value">{formatINR(profile.monthly_expenses)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Surplus</span>
              <span className="metric-value">{formatINR(profile.surplus)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">EMI outgo</span>
              <span className="metric-value">{formatINR(profile.emi_outgo)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Total debt</span>
              <span className="metric-value">{formatINR(profile.total_debt)}</span>
              <span className="metric-note">
                0 when statements omit outstanding principal
              </span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
