import { useEffect, useRef, useState } from "react";
import { applyPrefs, loadPrefs, savePrefs } from "../utils/prefs.js";

export default function SettingsMenu() {
  const [open, setOpen] = useState(false);
  const [prefs, setPrefs] = useState(() => loadPrefs());
  const panelRef = useRef(null);

  useEffect(() => {
    applyPrefs(prefs);
    savePrefs(prefs);
  }, [prefs]);

  useEffect(() => {
    function onDocClick(e) {
      if (!panelRef.current?.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", onDocClick);
      document.addEventListener("keydown", onKey);
    }
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function setTheme(theme) {
    setPrefs((p) => ({ ...p, theme }));
  }

  function setFontSize(fontSize) {
    setPrefs((p) => ({ ...p, fontSize }));
  }

  return (
    <div className="settings-wrap" ref={panelRef}>
      <button
        type="button"
        className="settings-btn"
        aria-label="Settings"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
            stroke="currentColor"
            strokeWidth="1.7"
          />
          <path
            d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.3.6.9 1 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {open && (
        <div className="settings-panel glass" role="dialog" aria-label="Display settings">
          <p className="settings-title">Display</p>

          <div className="settings-group">
            <span className="settings-label">Theme</span>
            <div className="segmented">
              {[
                { id: "light", label: "Light" },
                { id: "dark", label: "Dark" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className={prefs.theme === opt.id ? "seg active" : "seg"}
                  onClick={() => setTheme(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-group">
            <span className="settings-label">Font size</span>
            <div className="segmented">
              {[
                { id: "small", label: "Small" },
                { id: "medium", label: "Medium" },
                { id: "large", label: "Large" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className={prefs.fontSize === opt.id ? "seg active" : "seg"}
                  onClick={() => setFontSize(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
