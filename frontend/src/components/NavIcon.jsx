const STROKE = {
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function Svg({ children }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {children}
    </svg>
  );
}

const ICONS = {
  dashboard: (
    <Svg>
      <rect x="3" y="3" width="8" height="8" rx="1.5" {...STROKE} />
      <rect x="13" y="3" width="8" height="5" rx="1.5" {...STROKE} />
      <rect x="13" y="10" width="8" height="11" rx="1.5" {...STROKE} />
      <rect x="3" y="13" width="8" height="8" rx="1.5" {...STROKE} />
    </Svg>
  ),
  data: (
    <Svg>
      <circle cx="12" cy="8" r="3.5" {...STROKE} />
      <path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6" {...STROKE} />
      <path d="M17 5.5h3v3" {...STROKE} />
      <path d="M16 7.5l4-4" {...STROKE} />
    </Svg>
  ),
  transactions: (
    <Svg>
      <path d="M7 3h10l3 3v15H7V3z" {...STROKE} />
      <path d="M17 3v4h4" {...STROKE} />
      <path d="M10 11h6M10 15h4" {...STROKE} />
    </Svg>
  ),
  analytics: (
    <Svg>
      <path d="M4 20V10M10 20V4M16 20v-8M22 20H2" {...STROKE} />
    </Svg>
  ),
  budget: (
    <Svg>
      <path d="M4 8h16v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8z" {...STROKE} />
      <path d="M4 11h16M8 8V6a4 4 0 0 1 8 0v2" {...STROKE} />
      <circle cx="12" cy="15" r="1.25" fill="currentColor" stroke="none" />
    </Svg>
  ),
  investment: (
    <Svg>
      <path d="M4 18l6-6 4 4 6-8" {...STROKE} />
      <path d="M16 8h4v4" {...STROKE} />
    </Svg>
  ),
  portfolio: (
    <Svg>
      <circle cx="12" cy="12" r="8" {...STROKE} />
      <path d="M12 12l5-2.5" {...STROKE} />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
    </Svg>
  ),
  tax: (
    <Svg>
      <path d="M8 4h8l4 4v12H4V4h4z" {...STROKE} />
      <path d="M8 4v4h8V4M8 14h8M8 18h5" {...STROKE} />
    </Svg>
  ),
  coach: (
    <Svg>
      <path d="M4 5h16v10H8l-4 4V5z" {...STROKE} />
      <path d="M8 10h8M8 13h5" {...STROKE} />
    </Svg>
  ),
  premium: (
    <Svg>
      <path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z" {...STROKE} />
      <path d="M19 15l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9.9-2.1z" {...STROKE} />
    </Svg>
  ),
};

export default function NavIcon({ name }) {
  return ICONS[name] || ICONS.dashboard;
}
