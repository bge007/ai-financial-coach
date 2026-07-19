import GlassModal from "./GlassModal.jsx";

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

export default function AuthModal({
  mode,
  onClose,
  onSwitchMode,
  signup,
  setSignup,
  login,
  setLogin,
  error,
  loading,
  onSubmitSignup,
  onSubmitLogin,
}) {
  const isSignup = mode === "signup";

  return (
    <GlassModal open={Boolean(mode)} onClose={onClose} titleId="auth-modal-title" size="auth">
      <button type="button" className="glass-modal-close" onClick={onClose} aria-label="Close">
        ×
      </button>

      <div className="auth-modal-header">
        <img src="/moneymitra-logo.png" alt="" className="auth-modal-logo" aria-hidden="true" />
        <div>
          <h2 id="auth-modal-title">{isSignup ? "Create your account" : "Welcome back"}</h2>
          <p>
            {isSignup
              ? "Start with email and password — upload statements after sign in."
              : "Sign in to continue to your MoneyMitra dashboard."}
          </p>
        </div>
      </div>

      <div className="segmented landing-auth-tabs">
        <button
          type="button"
          className={isSignup ? "seg active" : "seg"}
          onClick={() => onSwitchMode("signup")}
        >
          Sign up
        </button>
        <button
          type="button"
          className={!isSignup ? "seg active" : "seg"}
          onClick={() => onSwitchMode("login")}
        >
          Log in
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      {isSignup ? (
        <form className="advisor-form auth-modal-form" onSubmit={onSubmitSignup}>
          <label className="field">
            <span>Name</span>
            <input
              required
              value={signup?.name ?? emptySignup.name}
              onChange={(e) => setSignup({ ...signup, name: e.target.value })}
              autoComplete="name"
            />
          </label>
          <label className="field">
            <span>Email ID</span>
            <input
              type="email"
              required
              value={signup?.email ?? emptySignup.email}
              onChange={(e) => setSignup({ ...signup, email: e.target.value })}
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Date of birth</span>
            <input
              type="date"
              required
              value={signup?.dob ?? emptySignup.dob}
              onChange={(e) => setSignup({ ...signup, dob: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Gender</span>
            <select
              value={signup?.gender ?? emptySignup.gender}
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
              value={signup?.password ?? emptySignup.password}
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
              value={signup?.confirm_password ?? emptySignup.confirm_password}
              onChange={(e) =>
                setSignup({ ...signup, confirm_password: e.target.value })
              }
              autoComplete="new-password"
            />
          </label>
          <button className="primary-btn advisor-run-btn" type="submit" disabled={loading}>
            {loading ? "Creating account…" : "Create free account"}
          </button>
        </form>
      ) : (
        <form className="advisor-form auth-modal-form" onSubmit={onSubmitLogin}>
          <label className="field">
            <span>Email ID</span>
            <input
              type="email"
              required
              value={login?.email ?? emptyLogin.email}
              onChange={(e) => setLogin({ ...login, email: e.target.value })}
              autoComplete="email"
              autoFocus
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              required
              value={login?.password ?? emptyLogin.password}
              onChange={(e) => setLogin({ ...login, password: e.target.value })}
              autoComplete="current-password"
            />
          </label>
          <button className="primary-btn advisor-run-btn" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Log in"}
          </button>
        </form>
      )}
    </GlassModal>
  );
}
