import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Shell from "./components/Shell.jsx";
import DataProfile from "./pages/DataProfile.jsx";
import Transactions from "./pages/Transactions.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import BudgetAdvisor from "./pages/BudgetAdvisor.jsx";
import InvestmentAdvisor from "./pages/InvestmentAdvisor.jsx";
import PortfolioOptimizer from "./pages/PortfolioOptimizer.jsx";
import TaxRetirement from "./pages/TaxRetirement.jsx";
import Coach from "./pages/Coach.jsx";
import MyMoneyMitra from "./pages/MyMoneyMitra.jsx";

export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", element: "dashboard", icon: "dashboard" },
  { path: "/data", label: "Data & Profile", element: "data", icon: "data" },
  { path: "/transactions", label: "Transactions", element: "transactions", icon: "transactions" },
  { path: "/analytics", label: "Analytics", element: "analytics", icon: "analytics" },
  { path: "/budget", label: "Budget Advisor", element: "budget", icon: "budget" },
  { path: "/investment", label: "Investment Advisor", element: "investment", icon: "investment" },
  { path: "/portfolio", label: "Portfolio Optimizer", element: "portfolio", icon: "portfolio" },
  { path: "/tax", label: "Tax & Retirement", element: "tax", icon: "tax" },
  { path: "/coach", label: "Ask the Coach", element: "coach", icon: "coach" },
  {
    path: "/premium",
    label: "My Money Mitra",
    sublabel: "Premium services",
    element: "premium",
    premium: true,
    icon: "premium",
  },
];

const PAGES = {
  dashboard: <Dashboard />,
  data: <DataProfile />,
  transactions: <Transactions />,
  analytics: <Analytics />,
  budget: <BudgetAdvisor />,
  investment: <InvestmentAdvisor />,
  portfolio: <PortfolioOptimizer />,
  tax: <TaxRetirement />,
  coach: <Coach />,
  premium: <MyMoneyMitra />,
};

function AuthenticatedApp({ user }) {
  const navigate = useNavigate();

  useEffect(() => {
    // Fresh session from landing signup/login lands on Data & Profile.
    if (sessionStorage.getItem("mm_post_auth") === "1") {
      sessionStorage.removeItem("mm_post_auth");
      navigate("/data", { replace: true });
    }
  }, [navigate]);

  return (
    <Routes>
      <Route element={<Shell user={user} />}>
        {NAV_ITEMS.map((item) => (
          <Route key={item.path} path={item.path} element={PAGES[item.element]} />
        ))}
        <Route path="*" element={<Navigate to="/data" replace />} />
      </Route>
    </Routes>
  );
}

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

  function handleAuthenticated(userBody) {
    sessionStorage.setItem("mm_post_auth", "1");
    setUser(userBody);
  }

  async function handleLogout() {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    setUser(null);
  }

  if (loading) {
    return <div className="center-screen loading-screen">MoneyMitra…</div>;
  }

  return (
    <Routes>
      <Route
        path="/welcome"
        element={
          <Landing
            user={user}
            onAuthenticated={handleAuthenticated}
            onLogout={handleLogout}
          />
        }
      />
      {user ? (
        <Route path="/*" element={<AuthenticatedApp user={user} />} />
      ) : (
        <Route
          path="/*"
          element={
            <Landing
              user={null}
              onAuthenticated={handleAuthenticated}
              onLogout={handleLogout}
            />
          }
        />
      )}
    </Routes>
  );
}
