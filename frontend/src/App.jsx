import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Shell from "./components/Shell.jsx";
import Stub from "./pages/Stub.jsx";

export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", phase: 6 },
  { path: "/data", label: "Data & Profile", phase: 1 },
  { path: "/transactions", label: "Transactions", phase: 2 },
  { path: "/analytics", label: "Analytics", phase: 6 },
  { path: "/budget", label: "Budget Advisor", phase: 6 },
  { path: "/investment", label: "Investment Advisor", phase: 6 },
  { path: "/portfolio", label: "Portfolio Optimizer", phase: 6 },
  { path: "/tax", label: "Tax & Retirement", phase: 6 },
  { path: "/coach", label: "Ask the Coach", phase: 6 },
];

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="center-screen">Loading…</div>;
  }

  if (!user) {
    return <Login />;
  }

  return (
    <Routes>
      <Route element={<Shell user={user} />}>
        {NAV_ITEMS.map((item) => (
          <Route
            key={item.path}
            path={item.path}
            element={<Stub label={item.label} phase={item.phase} />}
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
