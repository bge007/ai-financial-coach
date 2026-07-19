import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "../App.jsx";
import NavIcon from "./NavIcon.jsx";
import SettingsMenu from "./SettingsMenu.jsx";

function displayName(user) {
  const name = user?.name?.trim();
  if (name) return name;
  const email = user?.email || "";
  return email.split("@")[0] || "User";
}

function userInitials(user) {
  const name = displayName(user);
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export default function Shell({ user }) {
  async function logout() {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/";
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/welcome" className="brand brand-link">
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
        </NavLink>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                [
                  "nav-link",
                  item.premium ? "nav-link-premium" : "",
                  isActive ? "active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")
              }
            >
              <span className="nav-link-icon" aria-hidden="true">
                <NavIcon name={item.icon} />
              </span>
              <span className="nav-link-copy">
                <span className="nav-link-label">{item.label}</span>
                {item.sublabel ? (
                  <span className="nav-link-sub">{item.sublabel}</span>
                ) : null}
              </span>
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
          <div className="topbar-user" title={user.email}>
            <span className="topbar-avatar" aria-hidden="true">
              {userInitials(user)}
            </span>
            <div className="topbar-user-copy">
              <span className="topbar-greeting">Hello, {displayName(user)}</span>
              <span className="topbar-email">{user.email}</span>
            </div>
          </div>
          <div className="topbar-actions">
            <button type="button" className="topbar-logout-btn" onClick={logout}>
              Logout
            </button>
            <SettingsMenu />
          </div>
        </div>
        <Outlet />
        <footer className="footer-disclaimer">
          Informational only — not SEBI-registered investment advice. MoneyMitra.
        </footer>
      </main>
    </div>
  );
}
