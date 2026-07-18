import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "../App.jsx";
import SettingsMenu from "./SettingsMenu.jsx";

export default function Shell({ user }) {
  async function logout() {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/";
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img
            className="brand-logo"
            src="/moneymitra-logo.png"
            alt="MoneyMitra"
          />
          <div className="brand-copy">
            <span className="brand-name">
              Money<span className="mitra">Mitra</span>
            </span>
            <span className="brand-sub">Your trust, our guidance</span>
          </div>
        </div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="user-name" title={user.email}>{user.name || user.email}</span>
          <button className="logout-btn" onClick={logout}>Logout</button>
        </div>
      </aside>
      <main className="content">
        <div className="content-topbar">
          <SettingsMenu />
        </div>
        <Outlet />
        <footer className="footer-disclaimer">
          Informational only — not SEBI-registered investment advice. MoneyMitra.
        </footer>
      </main>
    </div>
  );
}
