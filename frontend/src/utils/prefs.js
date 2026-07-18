const STORAGE_KEY = "moneymitra.prefs";

const DEFAULTS = {
  theme: "light",
  fontSize: "medium",
};

export function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw);
    return {
      theme: parsed.theme === "dark" ? "dark" : "light",
      fontSize: ["small", "medium", "large"].includes(parsed.fontSize)
        ? parsed.fontSize
        : "medium",
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePrefs(prefs) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function applyPrefs(prefs) {
  const root = document.documentElement;
  root.dataset.theme = prefs.theme;
  root.dataset.fontSize = prefs.fontSize;
}
