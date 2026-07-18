import { useEffect, useRef, useState } from "react";

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export default function DataProfile() {
  const inputRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    const response = await fetch("/api/profile", { credentials: "include" });
    if (response.ok) {
      setProfile(await response.json());
    }
  }

  async function uploadFile(file) {
    if (!file) return;
    setUploading(true);
    setError("");
    setSummary(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail || "Upload failed");
      }
      setSummary(body);
      await loadProfile();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onDrop(event) {
    event.preventDefault();
    uploadFile(event.dataTransfer.files[0]);
  }

  return (
    <section className="data-page">
      <header className="page-header">
        <div>
          <h1>Data & Profile</h1>
          <p>Upload bank statements to build your deterministic financial profile.</p>
        </div>
      </header>

      <div className="data-grid">
        <div
          className="upload-zone"
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.pdf,text/csv,application/pdf"
            onChange={(event) => uploadFile(event.target.files[0])}
          />
          <div className="upload-title">Drop a CSV or PDF statement</div>
          <div className="upload-copy">10 MB max. Duplicates are detected by file hash.</div>
          <button
            type="button"
            className="primary-btn"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? "Uploading..." : "Choose file"}
          </button>
          {error && <div className="error-text">{error}</div>}
        </div>

        <ProfileCard profile={profile} />
      </div>

      {summary && <ParseSummary summary={summary} />}
    </section>
  );
}

function ProfileCard({ profile }) {
  const metrics = [
    ["Monthly income", profile?.monthly_income],
    ["Monthly expenses", profile?.monthly_expenses],
    ["Surplus", profile?.surplus],
    ["EMI outgo", profile?.emi_outgo],
    ["Total debt", profile?.total_debt],
    ["Transactions", profile?.transactions_count, "count"],
  ];

  return (
    <div className="profile-card">
      <div className="card-heading">
        <h2>Financial Profile</h2>
        <span>{profile?.computed_at ? "Updated" : "No data"}</span>
      </div>
      <div className="metric-grid">
        {metrics.map(([label, value, type]) => (
          <div className="metric" key={label}>
            <span>{label}</span>
            <strong>{formatValue(value, type)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ParseSummary({ summary }) {
  return (
    <div className="summary-band">
      <div>
        <span>Rows parsed</span>
        <strong>{summary.rows_parsed}</strong>
      </div>
      <div>
        <span>Rows added</span>
        <strong>{summary.rows_added}</strong>
      </div>
      <div>
        <span>Rows skipped</span>
        <strong>{summary.rows_skipped}</strong>
      </div>
      <div>
        <span>Date range</span>
        <strong>
          {summary.date_range.from} to {summary.date_range.to}
        </strong>
      </div>
      {summary.duplicate && <div className="duplicate-note">Duplicate upload</div>}
    </div>
  );
}

function formatValue(value, type) {
  if (value === undefined || value === null) return type === "count" ? "0" : money.format(0);
  if (type === "count") return value;
  return money.format(Number(value));
}
