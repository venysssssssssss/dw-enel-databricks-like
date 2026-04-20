"""Theme primitives for the ENEL Streamlit dashboards."""

from __future__ import annotations

from typing import Literal

ThemeMode = Literal["light", "dark"]

PALETTE = {
    "primary": "#2B2F36",
    "primary_dark": "#191C21",
    "primary_light": "#4A515B",
    "secondary": "#C8102E",
    "secondary_light": "#E4002B",
    "accent": "#1E7B55",
    "accent_soft": "#43A06F",
    "warning": "#E4002B",
    "neutral_950": "#111318",
    "neutral_900": "#1D1F24",
    "neutral_700": "#3C424B",
    "neutral_500": "#626B76",
    "neutral_200": "#DDE2EA",
    "neutral_100": "#EEF1F5",
    "neutral_50": "#F7F8FA",
    "surface": "#FFFFFF",
    "ce": "#C8102E",
    "sp": "#870A3C",
    "muted": "#626B76",
}

CATEGORICAL_SEQUENCE = [
    "#870A3C",
    "#C8102E",
    "#E4002B",
    "#1E7B55",
    "#2F6F9F",
    "#7B61A8",
    "#6F7682",
    "#43A06F",
]

SEQUENTIAL_BLUE = [
    "#FDECEF",
    "#F8C9D2",
    "#F19AAA",
    "#E85D74",
    "#E4002B",
    "#C8102E",
    "#A70D49",
    "#870A3C",
]

SEQUENTIAL_ORANGE = [
    "#FFF3E0",
    "#FFD9A6",
    "#FBB040",
    "#C8102E",
    "#E07B10",
    "#B86008",
]

SEQUENTIAL_GREEN = [
    "#E6F4EC",
    "#B6E0C5",
    "#80C89C",
    "#2BA65E",
    "#1E7B55",
    "#005F2C",
]


def css_variables(mode: ThemeMode = "light") -> dict[str, str]:
    """Return CSS variables for the selected visual mode — graphite oklch system."""
    if mode == "dark":
        return {
            "--enel-bg":            "oklch(17% 0.006 260)",
            "--enel-bg-soft":       "oklch(20% 0.006 260)",
            "--enel-bg-sidebar":    "oklch(14% 0.006 260)",
            "--enel-surface":       "oklch(20% 0.006 260)",
            "--enel-surface-2":     "oklch(23% 0.006 260)",
            "--enel-surface-3":     "oklch(26% 0.006 260)",
            "--enel-text":          "oklch(96% 0.002 260)",
            "--enel-muted":         "oklch(70% 0.004 260)",
            "--enel-text-dim":      "oklch(54% 0.004 260)",
            "--enel-text-faint":    "oklch(42% 0.004 260)",
            "--enel-border":        "oklch(28% 0.006 260)",
            "--enel-border-strong": "oklch(36% 0.006 260)",
            "--enel-divider":       "oklch(24% 0.006 260)",
            "--enel-shadow":        "0 20px 48px rgba(0,0,0,0.45)",
            "--enel-shadow-sm":     "0 1px 2px rgba(0,0,0,0.4)",
            "--enel-shadow-md":     "0 4px 14px rgba(0,0,0,0.35)",
            "--enel-accent-graphite": "oklch(58% 0.19 15)",
            "--enel-accent-hover":  "oklch(64% 0.20 15)",
            "--enel-accent-soft":   "oklch(58% 0.19 15 / 0.14)",
            "--enel-accent-ring":   "oklch(58% 0.19 15 / 0.28)",
        }
    return {
        "--enel-bg":            "oklch(97.2% 0.012 60)", # paper
        "--enel-bg-soft":       "oklch(95.5% 0.014 60)", # paper-2
        "--enel-bg-sidebar":    "oklch(95.5% 0.014 60)", # paper-2
        "--enel-surface":       "oklch(99% 0.006 60)",   # card
        "--enel-surface-2":     "oklch(93% 0.016 60)",   # paper-3
        "--enel-surface-3":     "oklch(96% 0.024 55)",   # warm-wash
        "--enel-text":          "oklch(22% 0.018 40)",   # ink
        "--enel-muted":         "oklch(36% 0.018 40)",   # ink-2
        "--enel-text-dim":      "oklch(52% 0.018 40)",   # ink-3
        "--enel-text-faint":    "oklch(68% 0.014 45)",   # ink-faint
        "--enel-border":        "oklch(89% 0.012 50)",   # line
        "--enel-border-strong": "oklch(82% 0.016 50)",   # line-strong
        "--enel-divider":       "oklch(89% 0.012 50)",
        "--enel-shadow":        "0 22px 48px oklch(22% 0.02 30 / 0.09), 0 4px 10px oklch(22% 0.02 30 / 0.05)",
        "--enel-shadow-sm":     "0 1px 2px oklch(22% 0.02 30 / 0.05)",
        "--enel-shadow-md":     "0 6px 18px oklch(22% 0.02 30 / 0.06), 0 2px 4px oklch(22% 0.02 30 / 0.04)",
        "--enel-accent-graphite": "oklch(60% 0.17 28)",  # terra
        "--enel-accent-hover":  "oklch(48% 0.17 24)",    # terra-deep
        "--enel-accent-soft":   "oklch(60% 0.17 28 / 0.10)",
        "--enel-accent-ring":   "oklch(60% 0.17 28 / 0.18)",
    }


def dashboard_css(mode: ThemeMode = "light") -> str:
    """Build Streamlit CSS with graphite design system, ENEL hierarchy and accessible contrast."""
    variables = "\n".join(f"{key}: {value};" for key, value in css_variables(mode).items())
    dark = mode == "dark"
    glass_bg = "rgba(29, 33, 40, 0.90)" if dark else "rgba(255, 255, 255, 0.92)"
    glass_border = "rgba(255, 255, 255, 0.14)" if dark else "rgba(28, 32, 38, 0.10)"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500&family=Inter+Tight:wght@500;600;700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
  {variables}
  --enel-primary: {PALETTE["primary"]};
  --enel-primary-light: {PALETTE["primary_light"]};
  --enel-secondary: {PALETTE["secondary"]};
  --enel-accent: {PALETTE["accent"]};
  --enel-warning: {PALETTE["warning"]};
  --enel-glass-bg: {glass_bg};
  --enel-glass-border: {glass_border};
  --enel-radius-lg: 8px;
  --enel-radius-md: 6px;
  --enel-radius-sm: 4px;

  /* ── Graphite shorthand aliases (used by new chat + sidebar components) ── */
  --bg:           var(--enel-bg);
  --bg-sidebar:   var(--enel-bg-sidebar);
  --surface:      var(--enel-surface);
  --surface-2:    var(--enel-surface-2);
  --surface-3:    var(--enel-surface-3);
  --border:       var(--enel-border);
  --border-strong: var(--enel-border-strong);
  --divider:      var(--enel-divider);
  --text:         var(--enel-text);
  --text-muted:   var(--enel-muted);
  --text-dim:     var(--enel-text-dim);
  --text-faint:   var(--enel-text-faint);
  --accent:       var(--enel-accent-graphite);
  --accent-hover: var(--enel-accent-hover);
  --accent-soft:  var(--enel-accent-soft);
  --accent-ring:  var(--enel-accent-ring);
  --ok:    oklch(70% 0.14 150);
  --warn:  oklch(74% 0.14 70);
  --crit:  oklch(64% 0.20 25);
  --font-display: 'Inter Tight', 'Inter', system-ui, -apple-system, sans-serif;
  --font-serif:   'Fraunces', 'Iowan Old Style', Georgia, serif;
  --font-body:    'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:    'JetBrains Mono', ui-monospace, 'SF Mono', monospace;
  /* ── Aconchegante warm tokens (story, hero accents, pareto gradient) ── */
  --warm-wash:    oklch(96% 0.022 55);
  --terra:        oklch(60% 0.17 28);
  --terra-deep:   oklch(48% 0.17 24);
  --plum:         oklch(36% 0.14 12);
  --plum-deep:    oklch(28% 0.12 10);
  --ease: cubic-bezier(0.2, 0.7, 0.2, 1);
  --r-xs: 4px; --r-sm: 6px; --r-md: 10px; --r-lg: 14px; --r-xl: 20px;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px;
  --shadow-sm: var(--enel-shadow-sm);
  --shadow-md: var(--enel-shadow-md);
  --shadow-lg: var(--enel-shadow);
}}

html, body, [class*="css"] {{
  font-family: var(--font-body);
  font-feature-settings: 'cv11', 'ss01', 'tnum';
  -webkit-font-smoothing: antialiased;
}}

h1, h2, h3, [data-testid="stMetricValue"] {{
  font-family: var(--font-display);
}}

code, pre, [data-testid="stMetricValue"], .enel-mono {{
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}}

.stApp {{
  background: var(--bg);
  color: var(--text);
  scroll-behavior: smooth;
}}

.block-container {{
  padding-top: 1.4rem;
  max-width: 1480px;
}}

/* ===== Métrica / card glass ===== */
[data-testid="stMetric"], .enel-card {{
  background: var(--enel-glass-bg);
  border: 1px solid var(--enel-glass-border);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-lg);
  padding: 1.15rem 1.2rem;
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
  transition: transform 220ms var(--ease),
              box-shadow 220ms ease,
              border-color 220ms ease;
}}
[data-testid="stMetric"]:hover, .enel-card:hover {{
  transform: translateY(-3px);
  border-color: rgba(200, 16, 46, 0.55);
  box-shadow: 0 28px 65px rgba(135, 10, 60, 0.18);
}}
[data-testid="stMetricLabel"] p {{
  font-size: 0.78rem; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-muted);
}}
[data-testid="stMetricValue"] {{
  font-size: 1.55rem !important;
  font-weight: 700 !important;
  letter-spacing: 0;
  color: var(--text) !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.82rem; font-weight: 600; }}

/* ===== Operational header ===== */
.enel-hero {{
  position: relative;
  overflow: hidden;
  border-radius: var(--r-lg);
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.2rem;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 5px solid var(--enel-secondary);
  box-shadow: var(--shadow-lg);
}}
.enel-hero h1 {{
  position: relative; z-index: 1;
  font-size: clamp(1.65rem, 3vw, 2.35rem);
  line-height: 1.03;
  letter-spacing: 0;
  margin: 0 0 0.45rem;
  font-weight: 800;
  color: var(--text) !important;
}}
.enel-hero p {{
  position: relative; z-index: 1;
  max-width: 880px;
  margin: 0;
  color: var(--text-muted) !important;
  font-size: 0.98rem;
  line-height: 1.5;
}}
.enel-hero .enel-hero-meta {{
  position: relative; z-index: 1;
  display: inline-flex; gap: 0.5rem; align-items: center;
  margin-top: 0.85rem;
  padding: 0.42rem 0.72rem;
  background: color-mix(in srgb, var(--enel-secondary) 10%, var(--surface) 90%);
  border-radius: var(--r-sm);
  font-weight: 700; font-size: 0.85rem;
  border: 1px solid color-mix(in srgb, var(--enel-secondary) 24%, var(--border) 76%);
  color: var(--text) !important;
}}

/* ===== Intro / chips ===== */
.enel-intro {{
  border-left: 4px solid var(--enel-secondary);
  background: color-mix(in srgb, var(--surface) 90%, var(--enel-secondary) 10%);
  border-radius: var(--r-lg);
  padding: 1rem 1.2rem;
  margin: 0.25rem 0 1rem;
  box-shadow: 0 1px 3px rgba(15,76,129,0.04);
}}
.enel-intro strong {{ color: var(--enel-primary); }}

.enel-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.7rem;
  margin: 0 0.35rem 0.35rem 0;
  border-radius: var(--r-sm);
  border: 1px solid var(--border);
  background: var(--enel-glass-bg);
  color: var(--text);
  font-size: 0.84rem;
  font-weight: 600;
  backdrop-filter: blur(8px);
  transition: transform 160ms ease, border-color 160ms ease;
}}
.enel-chip:hover {{
  transform: translateY(-1px);
  border-color: var(--accent);
}}

.enel-empty {{
  border: 1px dashed var(--border);
  background: var(--enel-glass-bg);
  border-radius: var(--r-lg);
  padding: 1.6rem;
  color: var(--text-muted);
  text-align: center;
  backdrop-filter: blur(8px);
}}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {{
  gap: 0.4rem;
  border-bottom: 1px solid var(--divider);
  padding-bottom: 0.2rem;
}}
.stTabs [data-baseweb="tab"] {{
  height: 48px;
  background: transparent;
  border-radius: var(--r-md) var(--r-md) 0 0;
  padding: 0 1.1rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 180ms ease, background 180ms ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: var(--text);
  background: color-mix(in srgb, var(--surface) 68%, var(--enel-secondary) 10%);
}}
.stTabs [aria-selected="true"] {{
  color: var(--text) !important;
  background: var(--enel-glass-bg) !important;
  border-bottom: 3px solid var(--accent) !important;
}}

/* ===== Sidebar — graphite premium ===== */
[data-testid="stSidebar"] {{
  background: var(--bg-sidebar);
  border-right: 1px solid var(--divider);
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
  margin-bottom: 0.25rem;
}}

/* Brand */
.sb-brand {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--divider);
  margin-bottom: 18px;
}}
.sb-brand-mark {{
  width: 28px; height: 28px;
  border-radius: 7px;
  background: linear-gradient(135deg, var(--accent) 0%, oklch(45% 0.18 15) 100%);
  display: grid; place-items: center;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
  box-shadow: inset 0 -6px 10px rgba(0,0,0,0.2), 0 1px 2px rgba(0,0,0,0.3);
  user-select: none;
}}
.sb-brand-text {{ display: flex; flex-direction: column; line-height: 1.15; }}
.sb-brand-name {{
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13.5px;
  letter-spacing: -0.01em;
  color: var(--text);
}}
.sb-brand-sub {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}

/* Section headers */
.sb-section {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 18px 0 8px;
}}
.sb-section-title {{
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-faint);
}}
.sb-section-badge {{
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  white-space: nowrap;
}}
.sb-section-link {{
  font-size: 11px;
  color: var(--text-dim);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dotted;
}}

/* Preset stack */
.preset-stack {{
  display: grid;
  gap: 3px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 4px;
  margin-bottom: 4px;
}}
.preset-item {{
  display: grid;
  grid-template-columns: 12px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 140ms var(--ease), color 140ms var(--ease);
  text-align: left;
  width: 100%;
  border: none;
  background: none;
  font-family: var(--font-body);
}}
.preset-item:hover {{ background: var(--surface-2); color: var(--text); }}
.preset-item .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-faint);
  display: inline-block;
  flex-shrink: 0;
}}
.preset-item .cmd {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}}
.preset-item.is-active {{
  background: var(--accent-soft);
  color: var(--text);
}}
.preset-item.is-active .dot {{
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}}
.preset-item.is-active .cmd {{
  color: var(--accent);
  background: transparent;
  border-color: var(--accent-ring);
}}

/* Hide native radio widget label that sits under the visual preset stack */
[data-testid="stSidebar"] [data-testid="stRadio"] > label {{
  display: none !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] > div {{
  gap: 2px;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{
  font-size: 12px;
  color: var(--text-muted);
}}

/* Toggle row */
.toggle-row {{
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  gap: 10px;
  margin-bottom: 6px;
}}
.toggle-row + .toggle-row {{ margin-top: 0; }}
.toggle-row .label-main {{
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
  margin: 0;
}}
.toggle-row .label-sub {{
  font-size: 11.5px;
  color: var(--text-dim);
  margin-top: 2px;
}}
/* Style native st.toggle to look like the refactor switch */
[data-testid="stSidebar"] [data-testid="stToggle"] {{
  margin: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] label {{
  display: none !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] [role="switch"] {{
  background-color: var(--surface-3) !important;
  border-color: var(--border-strong) !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] [aria-checked="true"] {{
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}}

/* Chip */
.chip {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 5px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  line-height: 1;
  margin: 2px;
}}
.chip.is-accent {{
  background: var(--accent-soft);
  border-color: var(--accent-ring);
  color: var(--text);
}}

/* Sidebar summary */
.sb-summary {{
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.55;
}}
.sb-summary b {{ color: var(--text); font-weight: 600; }}
.sb-summary .num {{
  font-family: var(--font-mono);
  color: var(--accent);
  font-weight: 600;
}}
.sb-summary-row {{
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
}}
.sb-summary-row + .sb-summary-row {{
  border-top: 1px dashed var(--divider);
}}

/* Multiselect tags — match chip style */
[data-baseweb="tag"] {{
  background-color: var(--accent-soft) !important;
  color: var(--text) !important;
  border: 1px solid var(--accent-ring) !important;
  border-radius: 5px !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
}}

/* ===== Animations — Sprint 17.3 ===== */
.js-plotly-plot,
[data-testid="stMetric"],
[data-baseweb="tab-panel"] > div {{
  animation: enelFade 320ms var(--ease) both;
}}
@keyframes enelFade {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }}
}}

/* ===== Dataframe polish ===== */
[data-testid="stDataFrame"] {{
  border-radius: var(--r-md);
  overflow: hidden;
  border: 1px solid var(--border);
}}

/* ===== Buttons — reforçados (Sprint 17.3) ===== */
.stButton > button {{
  border-radius: var(--r-md) !important;
  border: 1px solid var(--border-strong) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  font-weight: 600 !important;
  font-family: var(--font-body) !important;
  letter-spacing: 0.01em;
  padding: 0.55rem 1.05rem !important;
  box-shadow: var(--shadow-sm) !important;
  transition: transform 160ms var(--ease),
              box-shadow 180ms var(--ease),
              border-color 160ms var(--ease),
              background 160ms var(--ease);
}}
.stButton > button p,
.stButton > button span,
.stButton > button div {{
  color: var(--text) !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{
  transform: translateY(-1px);
  background: var(--accent-soft) !important;
  color: var(--text) !important;
  border-color: var(--accent) !important;
  box-shadow: 0 10px 22px var(--accent-ring) !important;
}}
.stButton > button:hover p,
.stButton > button:hover span,
.stButton > button:hover div {{
  color: var(--accent) !important;
}}
.stButton > button:active {{
  transform: translateY(0);
  box-shadow: var(--shadow-sm) !important;
}}
.stButton > button:focus-visible {{
  outline: 3px solid var(--accent-ring) !important;
  outline-offset: 2px !important;
}}
/* Primary CTA (kind="primary") */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
  box-shadow: 0 6px 18px var(--accent-ring) !important;
}}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[data-testid="baseButton-primary"] p,
.stButton > button[data-testid="baseButton-primary"] span {{
  color: #fff !important;
}}
.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.06);
  transform: translateY(-1px);
}}
/* Disabled — nítido em light+dark.
   Uses transparent background + dashed border so it reads as "not interactive"
   without disappearing into the page background in dark mode. */
.stButton > button:disabled,
.stButton > button[disabled] {{
  background: transparent !important;
  color: var(--text-faint) !important;
  border: 1px dashed var(--border-strong) !important;
  opacity: 1 !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
  transform: none !important;
}}
.stButton > button:disabled p,
.stButton > button:disabled span {{
  color: var(--text-faint) !important;
  font-weight: 500 !important;
}}

/* Download + form submit inherit from stButton */
[data-testid="stDownloadButton"] > button {{
  border-radius: var(--r-md) !important;
  border: 1px solid var(--border-strong) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  font-weight: 600 !important;
  box-shadow: var(--shadow-sm) !important;
  transition: transform 160ms var(--ease), border-color 160ms var(--ease), background 160ms var(--ease);
}}
[data-testid="stDownloadButton"] > button:hover {{
  background: var(--accent-soft) !important;
  border-color: var(--accent) !important;
  transform: translateY(-1px);
  color: var(--accent) !important;
}}

/* Clear filters button */
.stButton[data-key="sb_clear"] > button,
.sb-clear-btn > button {{
  width: 100% !important;
  color: var(--text-dim) !important;
  border: 1px dashed var(--border-strong) !important;
  background: transparent !important;
  text-align: center !important;
  margin-top: 8px;
  box-shadow: none !important;
}}
.stButton[data-key="sb_clear"] > button:hover,
.sb-clear-btn > button:hover {{
  color: var(--accent) !important;
  border-color: var(--accent-ring) !important;
  background: var(--accent-soft) !important;
  border-style: solid !important;
}}

/* ═══════ Premium components (Sprint 17.3 — Aconchegante absorbed) ═══════ */

/* ── Story block (onboarding por tela) ── */
.enel-story {{
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: flex-start;
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--accent-soft) 60%, var(--surface) 40%) 0%,
    var(--surface) 100%);
  border: 1px solid var(--accent-ring);
  border-left: 4px solid var(--accent);
  border-radius: var(--r-lg);
  padding: 16px 20px;
  margin: 0 0 18px;
  box-shadow: var(--shadow-sm);
  animation: enelFade 420ms var(--ease) both;
}}
.enel-story-icon {{
  width: 40px; height: 40px;
  border-radius: 10px;
  display: grid; place-items: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 18px;
  box-shadow: inset 0 -6px 10px rgba(0,0,0,0.2), 0 2px 4px rgba(0,0,0,0.2);
  user-select: none;
}}
.enel-story-body {{ font-size: 13.5px; color: var(--text-muted); line-height: 1.55; }}
.enel-story-body b {{ color: var(--text); font-weight: 600; }}
.enel-story-lead {{
  display: block;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
  color: var(--text);
  margin-bottom: 6px;
  line-height: 1.3;
}}
.enel-story-steps {{ display: flex; gap: 20px; margin-top: 12px; flex-wrap: wrap; }}
.enel-story-step {{ display: flex; gap: 8px; font-size: 12px; color: var(--text-dim); }}
.enel-story-step .n {{
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--accent);
  min-width: 14px;
}}

/* ── Insight callout (dentro de cards) ── */
.enel-insight {{
  margin-top: 14px;
  padding: 12px 14px 12px 16px;
  background: var(--surface-2);
  border-left: 3px solid var(--accent);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  font-size: 12.8px;
  color: var(--text-muted);
  line-height: 1.55;
}}
.enel-insight b {{ color: var(--text); font-weight: 600; }}
.enel-insight .label {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-right: 6px;
}}

/* ── KPI strip + dominant variant ── */
.enel-kpis {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}}
.enel-kpi {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  transition: transform 200ms var(--ease), box-shadow 200ms var(--ease), border-color 200ms var(--ease);
  position: relative;
  overflow: hidden;
  animation: enelFade 360ms var(--ease) both;
}}
.enel-kpi:hover {{
  transform: translateY(-3px);
  border-color: var(--accent-ring);
  box-shadow: 0 14px 30px rgba(16,20,28,0.09);
}}
.enel-kpi-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.enel-kpi-label {{
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.enel-kpi-tag {{
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-dim);
  border: 1px solid var(--border);
}}
.enel-kpi-val {{
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
  color: var(--text);
}}
.enel-kpi-sub {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 11.5px;
  color: var(--text-dim);
  font-family: var(--font-mono);
}}
.enel-kpi-sub .d-up {{ color: var(--crit); font-weight: 700; }}
.enel-kpi-sub .d-dn {{ color: var(--ok); font-weight: 700; }}
.enel-kpi.is-dominant {{
  background: linear-gradient(135deg, var(--accent-soft) 0%, var(--surface) 70%);
  border-color: var(--accent-ring);
}}
.enel-kpi.is-dominant .enel-kpi-val {{
  font-size: 20px;
  line-height: 1.2;
  color: var(--accent);
}}

/* ── DOM Pareto (nativo, sem plotly) ── */
.enel-pareto {{ display: grid; gap: 6px; }}
.enel-pareto-row {{
  display: grid;
  grid-template-columns: minmax(140px, 210px) 1fr 72px 54px;
  align-items: center;
  gap: 10px;
  padding: 8px 6px;
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background 140ms var(--ease);
}}
.enel-pareto-row:hover {{ background: var(--surface-2); }}
.enel-pareto-name {{
  font-size: 12.5px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.enel-pareto-bar {{
  position: relative;
  height: 22px;
  background: var(--surface-3);
  border-radius: 4px;
  overflow: hidden;
}}
.enel-pareto-fill {{
  position: absolute; top: 0; left: 0; height: 100%;
  background: linear-gradient(90deg, var(--accent) 0%, var(--accent-hover) 100%);
  border-radius: 4px;
  transform-origin: left center;
  animation: enelParetoGrow 620ms var(--ease) both;
}}
.enel-pareto-row.is-active .enel-pareto-fill {{
  background: linear-gradient(90deg, var(--accent-hover) 0%, var(--accent) 100%);
  box-shadow: 0 0 0 1px var(--accent-ring);
}}
.enel-pareto-row.is-active {{ background: var(--accent-soft); }}
.enel-pareto-val {{
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  text-align: right;
  font-weight: 700;
}}
.enel-pareto-pct {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  text-align: right;
}}
@keyframes enelParetoGrow {{
  from {{ transform: scaleX(0); }}
  to   {{ transform: scaleX(1); }}
}}

/* ── Health cards (Governança) ── */
.enel-health-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}}
.enel-health-card {{
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 16px 16px 20px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  animation: enelFade 360ms var(--ease) both;
  transition: transform 200ms var(--ease), box-shadow 200ms var(--ease);
}}
.enel-health-card:hover {{
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}}
.enel-health-card::before {{
  content: ''; position: absolute; left: 0; top: 0; bottom: 0;
  width: 4px;
  background: var(--ok);
}}
.enel-health-card.is-warn::before {{ background: var(--warn); }}
.enel-health-card.is-crit::before {{ background: var(--crit); }}
.enel-health-label {{
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.enel-health-value {{
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  margin: 6px 0 4px;
  letter-spacing: -0.01em;
  color: var(--text);
}}
.enel-health-sub {{
  font-size: 11.5px;
  color: var(--text-dim);
  font-family: var(--font-mono);
}}

/* ── Topic pills ── */
.enel-topics {{ display: flex; flex-wrap: wrap; gap: 4px 6px; }}
.enel-topic-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 11.5px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  cursor: default;
  transition: border-color 140ms var(--ease), color 140ms var(--ease), background 140ms var(--ease), transform 140ms var(--ease);
}}
.enel-topic-pill:hover {{
  border-color: var(--accent);
  color: var(--accent);
  background: var(--surface);
  transform: translateY(-1px);
}}
.enel-topic-pill .n {{ font-weight: 700; color: var(--text); }}
.enel-topic-pill:hover .n {{ color: var(--accent); }}

/* ── Segmented control ── */
.enel-seg {{
  display: inline-flex;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 3px;
  gap: 2px;
}}
.enel-seg button {{
  padding: 5px 12px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: 5px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 140ms var(--ease);
}}
.enel-seg button:hover {{ color: var(--text); }}
.enel-seg button.is-on {{
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-sm);
}}

/* ── Topbar status (pulse) ── */
.enel-topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0 16px;
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}}
.enel-crumbs b {{ color: var(--text); font-weight: 700; }}
.enel-status {{ display: inline-flex; align-items: center; gap: 10px; }}
.enel-pulse {{
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--ok) 50%, transparent);
  animation: enelPulse 2.4s infinite;
}}
@keyframes enelPulse {{
  0%   {{ box-shadow: 0 0 0 0 color-mix(in srgb, var(--ok) 55%, transparent); }}
  70%  {{ box-shadow: 0 0 0 10px color-mix(in srgb, var(--ok) 0%, transparent); }}
  100% {{ box-shadow: 0 0 0 0 color-mix(in srgb, var(--ok) 0%, transparent); }}
}}

/* ── Skeleton (consolidado e theme-aware) ── */
.enel-skeleton {{
  min-height: 96px;
  border-radius: var(--r-lg);
  background: linear-gradient(100deg,
    var(--surface-2) 20%,
    var(--surface-3) 40%,
    var(--surface-2) 60%);
  background-size: 220% 100%;
  border: 1px solid var(--border);
  animation: enelShimmer 1.2s ease-in-out infinite;
}}
@keyframes enelShimmer {{
  0%   {{ background-position: 120% 0; }}
  100% {{ background-position: -120% 0; }}
}}

/* ── Expander polish ── */
[data-testid="stExpander"] {{
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  background: var(--surface) !important;
  box-shadow: var(--shadow-sm);
}}
[data-testid="stExpander"] summary {{
  font-weight: 600;
  color: var(--text) !important;
}}
[data-testid="stExpander"] summary:hover {{ color: var(--accent) !important; }}

/* ===== Streamlit/BaseWeb contrast hardening ===== */
.stApp, .stMarkdown, .stText, .stCaption, .stDataFrame, label, p, li, span {{
  color: var(--text);
}}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] label {{
  color: var(--text);
}}
[data-baseweb="select"] > div,
[data-baseweb="popover"] div,
[data-baseweb="menu"] ul,
[data-testid="stDateInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stChatInput"] textarea {{
  background-color: var(--surface) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
}}
[data-baseweb="checkbox"] div,
[data-testid="stCheckbox"] div,
[data-testid="stToggle"] div {{
  color: var(--text) !important;
}}
[data-baseweb="checkbox"] [role="checkbox"],
[data-testid="stCheckbox"] [role="checkbox"] {{
  background-color: var(--surface-2) !important;
  border-color: var(--border) !important;
}}
[data-baseweb="checkbox"] [aria-checked="true"],
[data-testid="stCheckbox"] [aria-checked="true"] {{
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}}
[data-testid="stAlert"] {{
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
}}
a {{
  color: var(--accent);
}}
a:hover {{
  color: var(--accent-hover);
}}
</style>
"""


def plotly_template(mode: ThemeMode = "light") -> dict[str, object]:
    """Small Plotly layout template shared across layers."""
    dark = mode == "dark"
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, sans-serif", "color": "#F8F9FB" if dark else "#1D1F24"},
        "margin": {"l": 24, "r": 24, "t": 48, "b": 32},
        "hoverlabel": {"bgcolor": "#20232A" if dark else "#FFFFFF", "font_size": 13},
    }


def format_int(value: int | float) -> str:
    """Format integers for pt-BR dashboard cards."""
    return f"{int(value):,}".replace(",", ".")


def format_pct(value: float, *, scale: float = 100.0, digits: int = 1) -> str:
    """Format percentages where source values usually come as 0..1 rates."""
    return f"{value * scale:.{digits}f}%"
