import { useState } from "react";

const FEATURES = [
  {
    title: "Dashboard",
    blurb: "Income, expenses, surplus and a prioritised coach action plan at a glance.",
  },
  {
    title: "Data & Profile",
    blurb: "Upload bank CSV or PDF statements and ground every projection in your numbers.",
  },
  {
    title: "Transactions",
    blurb: "Auto-categorised debit and credit history with search and filters.",
  },
  {
    title: "Analytics",
    blurb: "Month-over-month spend, category mix, and top merchants.",
  },
  {
    title: "Budget Advisor",
    blurb: "50/30/20 needs–wants–savings check with clear next steps.",
  },
  {
    title: "Investment Advisor",
    blurb: "Risk-based allocation and long-term SIP corpus projections.",
  },
  {
    title: "Portfolio Optimizer",
    blurb: "Mean-variance weights, Sharpe ratio, and efficient frontier.",
  },
  {
    title: "Tax & Retirement",
    blurb: "Old vs new regime compare plus EPF / NPS retirement planning.",
  },
  {
    title: "Ask the Coach",
    blurb: "Multi-agent answers grounded in your statements — not invented figures.",
  },
];

const TESTIMONIALS = [
  {
    name: "Ananya R.",
    city: "Bengaluru",
    quote:
      "Finally a coach that shows the maths. The budget page made my EMI squeeze obvious in one glance.",
    initials: "AR",
  },
  {
    name: "Vikram S.",
    city: "Pune",
    quote:
      "Old vs new tax regime comparison saved me a long spreadsheet evening. Clear and trustworthy.",
    initials: "VS",
  },
  {
    name: "Meera K.",
    city: "Mumbai",
    quote:
      "SIP projection with editable assumptions felt honest. No flashy promises — just planning numbers.",
    initials: "MK",
  },
  {
    name: "Rahul D.",
    city: "Hyderabad",
    quote:
      "Uploading my ICICI PDF just worked. Transactions and analytics were ready in minutes.",
    initials: "RD",
  },
  {
    name: "Sneha P.",
    city: "Delhi NCR",
    quote:
      "Ask the Coach cited my own spend patterns. Felt personal without being pushy about products.",
    initials: "SP",
  },
];

const emptySignup = {
  name: "",
  email: "",
  dob: "",
  gender: "prefer_not_to_say",
  password: "",
  confirm_password: "",
};

const emptyLogin = {
  email: "",
  password: "",
};

function Stars() {
  return (
    <span className="landing-stars" aria-label="5 out of 5 stars">
      {"★★★★★"}
    </span>
  );
}

export default function Login({ onAuthenticated }) {
  const [mode, setMode] = useState("signup");
  const [signup, setSignup] = useState(emptySignup);
  const [login, setLogin] = useState(emptyLogin);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function scrollToAuth(nextMode) {
    setMode(nextMode);
    setError(null);
    document.getElementById("auth-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function submitSignup(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/auth/signup", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signup),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail = body.detail;
        const msg = Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : detail || "Signup failed";
        throw new Error(msg);
      }
      onAuthenticated?.(body);
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(login),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(body.detail || "Login failed");
      }
      onAuthenticated?.(body);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <div className="landing-brand">
          <img src="/moneymitra-logo.png" alt="MoneyMitra" className="landing-nav-logo" />
          <div>
            <span className="brand-name">
              Money<span className="mitra">Mitra</span>
            </span>
            <span className="brand-sub">Your trust, our guidance</span>
          </div>
        </div>
        <div className="landing-nav-actions">
          <button type="button" className="ghost-btn" onClick={() => scrollToAuth("login")}>
            Log in
          </button>
          <button type="button" className="primary-btn" onClick={() => scrollToAuth("signup")}>
            Sign up
          </button>
        </div>
      </header>

      <section className="landing-hero">
        <p className="page-kicker">Financial command centre for India</p>
        <h1>
          Money<span className="mitra">Mitra</span>
        </h1>
        <p className="landing-hero-lead">
          Multi-agent personal finance guidance grounded in your statements — budgets,
          investments, tax and retirement, with every ₹ figure from deterministic engines.
        </p>
        <div className="landing-hero-ctas">
          <button type="button" className="primary-btn" onClick={() => scrollToAuth("signup")}>
            Create free account
          </button>
          <button type="button" className="secondary-btn" onClick={() => scrollToAuth("login")}>
            I already have an account
          </button>
        </div>
      </section>

      <section className="landing-section" aria-labelledby="features-heading">
        <p className="page-kicker">What you get</p>
        <h2 id="features-heading">All features, one coach</h2>
        <p className="landing-section-sub">
          Built for salaried Indians who want clarity without product pushing.
        </p>
        <div className="landing-feature-grid">
          {FEATURES.map((f) => (
            <article className="landing-feature-card" key={f.title}>
              <h3>{f.title}</h3>
              <p>{f.blurb}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section" aria-labelledby="love-heading">
        <p className="page-kicker">Customer love</p>
        <h2 id="love-heading">5-star feedback from early users</h2>
        <p className="landing-section-sub">
          Composite stories from demo testers — illustrative for this product build.
        </p>
        <div className="landing-testimonial-grid">
          {TESTIMONIALS.map((t) => (
            <article className="landing-testimonial-card" key={t.name}>
              <div className="landing-testimonial-head">
                <div className="landing-avatar" aria-hidden="true">
                  {t.initials}
                </div>
                <div>
                  <strong>{t.name}</strong>
                  <span>{t.city}</span>
                </div>
              </div>
              <Stars />
              <p>“{t.quote}”</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-auth-section" id="auth-section">
        <p className="page-kicker">Get started</p>
        <h2>{mode === "signup" ? "Create your account" : "Welcome back"}</h2>
        <p className="landing-section-sub">
          Email and password only for this demo. After you sign in, you land on Data &amp; Profile.
        </p>

        <div className="landing-auth-card card">
          <div className="segmented landing-auth-tabs">
            <button
              type="button"
              className={mode === "signup" ? "seg active" : "seg"}
              onClick={() => {
                setMode("signup");
                setError(null);
              }}
            >
              Sign up
            </button>
            <button
              type="button"
              className={mode === "login" ? "seg active" : "seg"}
              onClick={() => {
                setMode("login");
                setError(null);
              }}
            >
              Log in
            </button>
          </div>

          {error && <div className="banner error">{error}</div>}

          {mode === "signup" ? (
            <form className="advisor-form" onSubmit={submitSignup}>
              <label className="field">
                <span>Name</span>
                <input
                  required
                  value={signup.name}
                  onChange={(e) => setSignup({ ...signup, name: e.target.value })}
                  autoComplete="name"
                />
              </label>
              <label className="field">
                <span>Email ID</span>
                <input
                  type="email"
                  required
                  value={signup.email}
                  onChange={(e) => setSignup({ ...signup, email: e.target.value })}
                  autoComplete="email"
                />
              </label>
              <label className="field">
                <span>Date of birth</span>
                <input
                  type="date"
                  required
                  value={signup.dob}
                  onChange={(e) => setSignup({ ...signup, dob: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Gender</span>
                <select
                  value={signup.gender}
                  onChange={(e) => setSignup({ ...signup, gender: e.target.value })}
                >
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other</option>
                  <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
              </label>
              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={signup.password}
                  onChange={(e) => setSignup({ ...signup, password: e.target.value })}
                  autoComplete="new-password"
                />
              </label>
              <label className="field">
                <span>Confirm password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={signup.confirm_password}
                  onChange={(e) =>
                    setSignup({ ...signup, confirm_password: e.target.value })
                  }
                  autoComplete="new-password"
                />
              </label>
              <button className="primary-btn advisor-run-btn" type="submit" disabled={loading}>
                {loading ? "Creating account…" : "Sign up"}
              </button>
            </form>
          ) : (
            <form className="advisor-form" onSubmit={submitLogin}>
              <label className="field">
                <span>Email ID</span>
                <input
                  type="email"
                  required
                  value={login.email}
                  onChange={(e) => setLogin({ ...login, email: e.target.value })}
                  autoComplete="email"
                />
              </label>
              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  required
                  value={login.password}
                  onChange={(e) => setLogin({ ...login, password: e.target.value })}
                  autoComplete="current-password"
                />
              </label>
              <button className="primary-btn advisor-run-btn" type="submit" disabled={loading}>
                {loading ? "Signing in…" : "Log in"}
              </button>
            </form>
          )}
        </div>
      </section>

      <footer className="landing-footer">
        Informational only — not SEBI-registered investment advice. MoneyMitra.
      </footer>
    </div>
  );
}
