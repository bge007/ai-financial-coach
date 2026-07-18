import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login.jsx";
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

export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", element: "dashboard" },
  { path: "/data", label: "Data & Profile", element: "data" },
  { path: "/transactions", label: "Transactions", element: "transactions" },
  { path: "/analytics", label: "Analytics", element: "analytics" },
  { path: "/budget", label: "Budget Advisor", element: "budget" },
  { path: "/investment", label: "Investment Advisor", element: "investment" },
  { path: "/portfolio", label: "Portfolio Optimizer", element: "portfolio" },
  { path: "/tax", label: "Tax & Retirement", element: "tax" },
  { path: "/coach", label: "Ask the Coach", element: "coach" },
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
};

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
    return <div className="center-screen loading-screen">MoneyMitra…</div>;
  }

  if (!user) {
    return <Login />;
  }

  return (
    <Routes>
      <Route element={<Shell user={user} />}>
        {NAV_ITEMS.map((item) => (
          <Route key={item.path} path={item.path} element={PAGES[item.element]} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
