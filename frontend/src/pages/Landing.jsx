import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import AuthModal from "../components/AuthModal.jsx";
import FeatureModal from "../components/FeatureModal.jsx";

const HERO_SLIDES = [
  {
    tag: "Built for India",
    title: "Your money, decoded with trust",
    text: "Upload bank CSV or PDF statements and get budgets, tax, SIP and retirement plans — every ₹ from deterministic engines, not guesswork.",
    accent: "growth",
  },
  {
    tag: "Multi-agent coach",
    title: "Nine specialists. One dashboard.",
    text: "Budget, investment, portfolio, tax and retirement advisors work together — LangGraph routes your questions to the right expert.",
    accent: "gold",
  },
  {
    tag: "Ask the Coach",
    title: "Answers grounded in your data",
    text: "RAG-powered chat cites your own transactions and profile. No invented Sharpe ratios or tax figures — ever.",
    accent: "primary",
  },
];

const STATS = [
  { value: "9", label: "Finance modules" },
  { value: "100%", label: "Deterministic maths" },
  { value: "FY26-27", label: "Indian tax config" },
  { value: "CSV + PDF", label: "Statement upload" },
];

const FEATURES = [
  {
    icon: "📊",
    title: "Dashboard",
    blurb: "Income, expenses, surplus and a prioritised coach action plan at a glance.",
    details: [
      "Monthly income, expense and surplus snapshot",
      "Debt overview with coach action plan",
      "Visual bars for quick financial health check",
    ],
  },
  {
    icon: "📁",
    title: "Data & Profile",
    blurb: "Upload bank CSV or PDF statements and ground every projection in your numbers.",
    details: [
      "HDFC, ICICI, SBI and generic CSV support",
      "PDF statement parsing for major Indian banks",
      "Profile built from your real transaction history",
    ],
  },
  {
    icon: "💳",
    title: "Transactions",
    blurb: "Auto-categorised debit and credit history with search and filters.",
    details: [
      "AI categorisation: rent, SIP, EMI, groceries, travel",
      "Search and filter by category or date",
      "Paginated history with export-ready views",
    ],
  },
  {
    icon: "📈",
    title: "Analytics",
    blurb: "Month-over-month spend, category mix, and top merchants.",
    details: [
      "Month-over-month spend trend charts",
      "Category breakdown pie and bar views",
      "Top merchants and income vs expense tracking",
    ],
  },
  {
    icon: "🎯",
    title: "Budget Advisor",
    blurb: "50/30/20 needs–wants–savings check with clear next steps.",
    details: [
      "Live 50/30/20 needs–wants–savings analysis",
      "Actual vs target comparison with nudges",
      "Deterministic budget engine — no invented numbers",
    ],
  },
  {
    icon: "💹",
    title: "Investment Advisor",
    blurb: "Risk-based allocation and long-term SIP corpus projections.",
    details: [
      "Risk profile → equity / bonds / cash split",
      "20-year SIP growth projection charts",
      "Editable assumptions you can trust",
    ],
  },
  {
    icon: "⚖️",
    title: "Portfolio Optimizer",
    blurb: "Mean-variance weights, Sharpe ratio, and efficient frontier.",
    details: [
      "Mean-variance optimisation (MVO) weights",
      "Sharpe ratio and efficient frontier visualisation",
      "15-year corpus projection from optimised portfolio",
    ],
  },
  {
    icon: "🧾",
    title: "Tax & Retirement",
    blurb: "Old vs new regime compare plus EPF / NPS retirement planning.",
    details: [
      "Old vs new tax regime side-by-side (FY 2026–27)",
      "80C limits and deduction-aware comparison",
      "EPF, NPS and SIP retirement runway projections",
    ],
  },
  {
    icon: "🤖",
    title: "Ask the Coach",
    blurb: "Multi-agent answers grounded in your statements — not invented figures.",
    details: [
      "LangGraph multi-agent routing to specialists",
      "RAG answers grounded in your uploaded documents",
      "Prepay loan vs invest surplus — with your real numbers",
    ],
  },
];

const PROJECTS = [
  {
    name: "Budget Command Centre",
    module: "Budget Advisor",
    desc: "Live 50/30/20 analysis with actual vs target bars and actionable nudges.",
    gradient: "from-navy",
  },
  {
    name: "Wealth Blueprint",
    module: "Investment + Portfolio",
    desc: "Risk profile → allocation pie → MVO weights → 15-year corpus projection.",
    gradient: "from-green",
  },
  {
    name: "Tax Clarity Kit",
    module: "Tax & Retirement",
    desc: "Old vs new regime side-by-side with 80C, EPF and NPS retirement runway.",
    gradient: "from-gold",
  },
  {
    name: "Statement Intelligence",
    module: "Data + Transactions",
    desc: "HDFC, ICICI, SBI CSV/PDF ingestion with AI categorisation in minutes.",
    gradient: "from-teal",
  },
];

const TESTIMONIALS = [
  {
    name: "Ananya R.",
    city: "Bengaluru",
    role: "Product manager",
    quote:
      "Finally a coach that shows the maths. The budget page made my EMI squeeze obvious in one glance.",
    initials: "AR",
  },
  {
    name: "Vikram S.",
    city: "Pune",
    role: "Software engineer",
    quote:
      "Old vs new tax regime comparison saved me a long spreadsheet evening. Clear and trustworthy.",
    initials: "VS",
  },
  {
    name: "Meera K.",
    city: "Mumbai",
    role: "Chartered accountant",
    quote:
      "SIP projection with editable assumptions felt honest. No flashy promises — just planning numbers.",
    initials: "MK",
  },
  {
    name: "Rahul D.",
    city: "Hyderabad",
    role: "Startup founder",
    quote:
      "Uploading my ICICI PDF just worked. Transactions and analytics were ready in minutes.",
    initials: "RD",
  },
  {
    name: "Sneha P.",
    city: "Delhi NCR",
    role: "Marketing lead",
    quote:
      "Ask the Coach cited my own spend patterns. Felt personal without being pushy about products.",
    initials: "SP",
  },
];

const FAQS = [
  {
    id: "what-is-moneymitra",
    question: "What is MoneyMitra?",
    answer:
      "MoneyMitra is an AI personal finance companion built for India. Upload your bank statements, get auto-categorised transactions, and use nine modules — budget, investment, tax, retirement, and more — with every ₹ figure from deterministic engines.",
  },
  {
    id: "investment-advice",
    question: "Is MoneyMitra SEBI-registered investment advice?",
    answer:
      "No. MoneyMitra is for informational and educational purposes only. It helps you understand your finances and explore scenarios — it does not provide SEBI-registered investment advice or product recommendations.",
  },
  {
    id: "statement-upload",
    question: "Which bank statements can I upload?",
    answer:
      "You can upload CSV exports and PDF statements from major Indian banks including HDFC, ICICI, and SBI. Generic CSV formats are also supported. After upload, transactions are parsed and categorised automatically.",
  },
  {
    id: "numbers-trust",
    question: "How do I know the numbers are accurate?",
    answer:
      "All financial calculations — tax, SIP projections, Sharpe ratios, budget splits — come from deterministic engines in the backend. The AI explains and orchestrates; it never invents tax figures or portfolio metrics.",
  },
  {
    id: "ask-coach",
    question: "What does “Ask the Coach” do?",
    answer:
      "Ask the Coach is a multi-agent chat grounded in your own uploaded documents via RAG. Questions like “prepay my loan or invest surplus?” are routed to specialist agents and answered using your real transaction and profile data.",
  },
  {
    id: "data-privacy",
    question: "Is my financial data private?",
    answer:
      "Your data is stored per user account with isolated collections. Statements and profiles are used only to power your dashboard and coach answers — not shared across users or used to sell financial products.",
  },
  {
    id: "pricing",
    question: "Do I need to pay or add a credit card?",
    answer:
      "No credit card is required for this demo. Create a free account with email and password, upload a sample statement, and explore all modules. Optional API keys (e.g. OpenRouter) enrich coach chat but are not mandatory.",
  },
  {
    id: "tax-regime",
    question: "Can MoneyMitra compare old vs new tax regime?",
    answer:
      "Yes. The Tax & Retirement module compares old and new regime side-by-side using FY 2026–27 slabs from versioned config files, including 80C limits, EPF, and NPS retirement projections.",
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

function useReveal() {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    el.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  return ref;
}

export default function Landing({ onAuthenticated, user: userProp, onLogout }) {
  const navigate = useNavigate();
  const pageRef = useReveal();
  const [sessionUser, setSessionUser] = useState(userProp || null);
  const [authChecked, setAuthChecked] = useState(Boolean(userProp));
  const [authModal, setAuthModal] = useState(null);
  const [featureModal, setFeatureModal] = useState(null);
  const [heroIndex, setHeroIndex] = useState(0);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [signup, setSignup] = useState(emptySignup);
  const [login, setLogin] = useState(emptyLogin);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [openFaqId, setOpenFaqId] = useState(null);

  useEffect(() => {
    if (userProp) {
      setSessionUser(userProp);
      setAuthChecked(true);
      return;
    }
    fetch("/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((body) => setSessionUser(body))
      .catch(() => setSessionUser(null))
      .finally(() => setAuthChecked(true));
  }, [userProp]);

  const currentUser = userProp || sessionUser;

  async function handleLogout() {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    setSessionUser(null);
    onLogout?.();
  }

  function openDashboard() {
    if (currentUser) {
      onAuthenticated?.(currentUser);
      navigate("/data");
    }
  }

  const scrollToSection = useCallback((sectionId) => {
    const el = document.getElementById(sectionId);
    if (!el) return;

    const nav = document.querySelector(".landing-nav");
    const offset = (nav?.offsetHeight ?? 72) + 16;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;

    window.scrollTo({ top, behavior: "smooth" });
  }, []);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const openAuth = useCallback((mode) => {
    setError(null);
    setAuthModal(mode);
  }, []);

  const closeAuth = useCallback(() => {
    setAuthModal(null);
    setError(null);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setHeroIndex((i) => (i + 1) % HERO_SLIDES.length);
    }, 5500);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setReviewIndex((i) => (i + 1) % TESTIMONIALS.length);
    }, 7000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    function onScroll() {
      setShowScrollTop(window.scrollY > 420);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

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
      closeAuth();
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
      closeAuth();
      onAuthenticated?.(body);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  const activeReview = TESTIMONIALS[reviewIndex];
  const activeHero = HERO_SLIDES[heroIndex];

  return (
    <div className="landing-page" ref={pageRef}>
      <div className="landing-bg-shapes" aria-hidden="true">
        <span className="landing-blob landing-blob-1" />
        <span className="landing-blob landing-blob-2" />
        <span className="landing-blob landing-blob-3" />
      </div>

      <header className="landing-nav landing-animate-slide-down">
        <div className="landing-brand">
          <img src="/moneymitra-logo.png" alt="MoneyMitra" className="landing-nav-logo" />
          <div>
            <span className="brand-name">
              Money<span className="mitra">Mitra</span>
            </span>
            <span className="brand-sub">Your trust, our guidance</span>
          </div>
        </div>
        <nav className="landing-nav-links" aria-label="Page sections">
          <a
            href="#features"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection("features");
            }}
          >
            Features
          </a>
          <a
            href="#projects"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection("projects");
            }}
          >
            Modules
          </a>
          <a
            href="#reviews"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection("reviews");
            }}
          >
            Reviews
          </a>
          <a
            href="#faq"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection("faq");
            }}
          >
            FAQ
          </a>
        </nav>
        <div className="landing-nav-actions">
          {currentUser ? (
            <button type="button" className="ghost-btn landing-logout-btn" onClick={handleLogout}>
              Logout
            </button>
          ) : authChecked ? (
            <>
              <button type="button" className="ghost-btn" onClick={() => openAuth("login")}>
                Log in
              </button>
              <button type="button" className="primary-btn" onClick={() => openAuth("signup")}>
                Sign up
              </button>
            </>
          ) : null}
        </div>
      </header>

      <section className="landing-hero-banner">
        <div className="landing-hero-grid">
          <div className="landing-hero-copy reveal">
            <p className="page-kicker landing-animate-fade-in">{activeHero.tag}</p>
            <h1 key={heroIndex} className="landing-hero-title landing-animate-fade-up">
              {activeHero.title}
            </h1>
            <p key={`t-${heroIndex}`} className="landing-hero-lead landing-animate-fade-in">
              {activeHero.text}
            </p>
            <div className="landing-hero-ctas reveal">
              {currentUser ? (
                <>
                  <button type="button" className="primary-btn landing-btn-glow" onClick={openDashboard}>
                    Go to dashboard
                  </button>
                  <button type="button" className="secondary-btn" onClick={handleLogout}>
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button type="button" className="primary-btn landing-btn-glow" onClick={() => openAuth("signup")}>
                    Get started free
                  </button>
                  <button type="button" className="secondary-btn" onClick={() => openAuth("login")}>
                    Log in
                  </button>
                </>
              )}
            </div>
            <div className="landing-hero-dots" role="tablist" aria-label="Hero banners">
              {HERO_SLIDES.map((slide, i) => (
                <button
                  key={slide.tag}
                  type="button"
                  role="tab"
                  aria-selected={i === heroIndex}
                  className={i === heroIndex ? "dot active" : "dot"}
                  onClick={() => setHeroIndex(i)}
                />
              ))}
            </div>
          </div>

          <div className="landing-hero-visual reveal">
            <div className={`landing-hero-card accent-${activeHero.accent}`}>
              <div className="landing-hero-card-top">
                <span className="landing-pill">Live preview</span>
                <span className="landing-pill muted">FY 2026–27</span>
              </div>
              <div className="landing-mock-stats">
                <div className="landing-mock-stat">
                  <span>Income</span>
                  <strong>₹1,42,000</strong>
                </div>
                <div className="landing-mock-stat">
                  <span>Surplus</span>
                  <strong className="positive">₹28,400</strong>
                </div>
                <div className="landing-mock-stat">
                  <span>Savings rate</span>
                  <strong>20%</strong>
                </div>
              </div>
              <div className="landing-mock-bars">
                <div style={{ width: "50%" }} className="bar needs" title="Needs 50%" />
                <div style={{ width: "30%" }} className="bar wants" title="Wants 30%" />
                <div style={{ width: "20%" }} className="bar save" title="Savings 20%" />
              </div>
              <p className="landing-mock-caption">50/30/20 budget check — powered by your statements</p>
            </div>
            <div className="landing-float-card landing-float-card-1 landing-animate-float">
              <span>📈</span> SIP corpus ₹1.2 Cr
            </div>
            <div className="landing-float-card landing-float-card-2 landing-animate-float-delay">
              <span>🧾</span> Tax saved ₹18,400
            </div>
          </div>
        </div>
      </section>

      <section className="landing-stats reveal" aria-label="Key metrics">
        {STATS.map((s, i) => (
          <div key={s.label} className="landing-stat" style={{ animationDelay: `${i * 0.08}s` }}>
            <strong>{s.value}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </section>

      <section className="landing-section" id="features" aria-labelledby="features-heading">
        <div className="landing-section-head reveal">
          <p className="page-kicker">What you get</p>
          <h2 id="features-heading">All features, one coach</h2>
          <p className="landing-section-sub">
            Built for salaried Indians who want clarity without product pushing.
          </p>
        </div>
        <div className="landing-feature-grid">
          {FEATURES.map((f, i) => (
            <button
              type="button"
              className="landing-feature-tile reveal"
              key={f.title}
              style={{ transitionDelay: `${(i % 3) * 0.08}s` }}
              onClick={() => setFeatureModal(f)}
            >
              <span className="landing-feature-icon" aria-hidden="true">
                {f.icon}
              </span>
              <h3>{f.title}</h3>
              <p>{f.blurb}</p>
              <span className="landing-feature-link">View details →</span>
            </button>
          ))}
        </div>
      </section>

      <section className="landing-section landing-projects" id="projects" aria-labelledby="projects-heading">
        <div className="landing-section-head reveal">
          <p className="page-kicker">Product modules</p>
          <h2 id="projects-heading">Four journeys, nine tools</h2>
          <p className="landing-section-sub">
            Each module combines deterministic engines with AI explanation — numbers you can verify.
          </p>
        </div>
        <div className="landing-project-grid">
          {PROJECTS.map((p, i) => (
            <article
              className={`landing-project-card ${p.gradient} reveal`}
              key={p.name}
              style={{ transitionDelay: `${i * 0.1}s` }}
            >
              <span className="landing-project-module">{p.module}</span>
              <h3>{p.name}</h3>
              <p>{p.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-reviews" id="reviews" aria-labelledby="reviews-heading">
        <div className="landing-section-head reveal">
          <p className="page-kicker">Customer love</p>
          <h2 id="reviews-heading">Trusted by early adopters</h2>
          <p className="landing-section-sub">
            Composite stories from demo testers — illustrative for this product build.
          </p>
        </div>

        <div className="landing-carousel reveal">
          <article className="landing-carousel-slide landing-animate-fade-in" key={reviewIndex}>
            <div className="landing-testimonial-head">
              <div className="landing-avatar" aria-hidden="true">
                {activeReview.initials}
              </div>
              <div>
                <strong>{activeReview.name}</strong>
                <span>
                  {activeReview.city} · {activeReview.role}
                </span>
              </div>
            </div>
            <Stars />
            <blockquote>“{activeReview.quote}”</blockquote>
          </article>

          <div className="landing-carousel-controls">
            <button
              type="button"
              className="ghost-btn landing-carousel-btn"
              aria-label="Previous review"
              onClick={() =>
                setReviewIndex((i) => (i - 1 + TESTIMONIALS.length) % TESTIMONIALS.length)
              }
            >
              ←
            </button>
            <div className="landing-carousel-dots">
              {TESTIMONIALS.map((t, i) => (
                <button
                  key={t.name}
                  type="button"
                  className={i === reviewIndex ? "dot active" : "dot"}
                  aria-label={`Review ${i + 1}`}
                  onClick={() => setReviewIndex(i)}
                />
              ))}
            </div>
            <button
              type="button"
              className="ghost-btn landing-carousel-btn"
              aria-label="Next review"
              onClick={() => setReviewIndex((i) => (i + 1) % TESTIMONIALS.length)}
            >
              →
            </button>
          </div>
        </div>
      </section>

      <section className="landing-section landing-faq" id="faq" aria-labelledby="faq-heading">
        <div className="landing-section-head reveal">
          <p className="page-kicker">Questions answered</p>
          <h2 id="faq-heading">Frequently asked questions</h2>
          <p className="landing-section-sub">
            Everything you need to know before uploading your first statement.
          </p>
        </div>

        <div className="landing-faq-list reveal">
          {FAQS.map((faq, i) => {
            const isOpen = openFaqId === faq.id;
            const panelId = `faq-panel-${faq.id}`;
            const buttonId = `faq-button-${faq.id}`;

            return (
              <article
                key={faq.id}
                className={`landing-faq-item${isOpen ? " open" : ""}`}
                style={{ transitionDelay: `${(i % 4) * 0.05}s` }}
              >
                <h3 className="landing-faq-question">
                  <button
                    type="button"
                    id={buttonId}
                    className="landing-faq-trigger"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpenFaqId(isOpen ? null : faq.id)}
                  >
                    <span>{faq.question}</span>
                    <span className="landing-faq-icon" aria-hidden="true">
                      {isOpen ? "−" : "+"}
                    </span>
                  </button>
                </h3>
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  className="landing-faq-panel"
                  hidden={!isOpen}
                >
                  <p>{faq.answer}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="landing-cta-banner reveal" aria-labelledby="cta-heading">
        <div className="landing-cta-shell">
          <div className="landing-cta-glow landing-cta-glow-1" aria-hidden="true" />
          <div className="landing-cta-glow landing-cta-glow-2" aria-hidden="true" />
          <div className="landing-cta-grid">
            <div className="landing-cta-copy">
              <p className="landing-cta-badge">
                <span className="landing-cta-badge-dot" aria-hidden="true" />
                Start free · No credit card
              </p>
              <h2 id="cta-heading">Ready to plan with confidence?</h2>
              <p className="landing-cta-lead">
                Join thousands of Indians who want clarity over hype. Upload your first bank
                statement and see budgets, tax, and investments grounded in your real numbers.
              </p>

              <ul className="landing-cta-perks" aria-label="Benefits">
                <li>
                  <span aria-hidden="true">⚡</span>
                  Live in under 5 minutes
                </li>
                <li>
                  <span aria-hidden="true">📄</span>
                  CSV &amp; PDF statement upload
                </li>
                <li>
                  <span aria-hidden="true">🔒</span>
                  Your data stays private
                </li>
              </ul>

              <div className="landing-cta-actions">
                {currentUser ? (
                  <>
                    <button
                      type="button"
                      className="primary-btn landing-cta-primary"
                      onClick={openDashboard}
                    >
                      Go to dashboard
                      <span className="landing-cta-btn-arrow" aria-hidden="true">→</span>
                    </button>
                    <button type="button" className="landing-cta-ghost" onClick={handleLogout}>
                      Logout
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="primary-btn landing-cta-primary"
                      onClick={() => openAuth("signup")}
                    >
                      Create free account
                      <span className="landing-cta-btn-arrow" aria-hidden="true">→</span>
                    </button>
                    <button type="button" className="landing-cta-ghost" onClick={() => openAuth("login")}>
                      Log in
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="landing-cta-visual" aria-hidden="true">
              <div className="landing-cta-glass-card landing-cta-glass-main landing-animate-float">
                <div className="landing-cta-glass-head">
                  <img src="/moneymitra-logo.png" alt="" className="landing-cta-mini-logo" />
                  <div>
                    <strong>MoneyMitra</strong>
                    <span>Your financial command centre</span>
                  </div>
                </div>
                <div className="landing-cta-mini-metrics">
                  <div>
                    <span>Modules</span>
                    <strong>9</strong>
                  </div>
                  <div>
                    <span>Tax FY</span>
                    <strong>26-27</strong>
                  </div>
                  <div>
                    <span>Accuracy</span>
                    <strong>100%</strong>
                  </div>
                </div>
                <div className="landing-cta-progress">
                  <div className="landing-cta-progress-bar" />
                </div>
                <p className="landing-cta-glass-caption">Deterministic engines · AI explanation</p>
              </div>

              <div className="landing-cta-chip landing-cta-chip-1 landing-animate-float-delay">
                <span>📊</span> Dashboard ready
              </div>
              <div className="landing-cta-chip landing-cta-chip-2 landing-animate-float">
                <span>🤖</span> Ask the Coach
              </div>
              <div className="landing-cta-chip landing-cta-chip-3 landing-animate-float-delay">
                <span>🧾</span> Tax saved ₹18K+
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        Informational only — not SEBI-registered investment advice. MoneyMitra © 2026
      </footer>

      <AuthModal
        mode={authModal}
        onClose={closeAuth}
        onSwitchMode={(m) => {
          setError(null);
          setAuthModal(m);
        }}
        signup={signup}
        setSignup={setSignup}
        login={login}
        setLogin={setLogin}
        error={error}
        loading={loading}
        onSubmitSignup={submitSignup}
        onSubmitLogin={submitLogin}
      />

      <FeatureModal
        feature={featureModal}
        onClose={() => setFeatureModal(null)}
        onGetStarted={() => {
          setFeatureModal(null);
          openAuth("signup");
        }}
      />

      <button
        type="button"
        className={`scroll-top-btn${showScrollTop ? " visible" : ""}`}
        onClick={scrollToTop}
        aria-label="Scroll to top"
        title="Back to top"
      >
        <span aria-hidden="true">↑</span>
      </button>
    </div>
  );
}
