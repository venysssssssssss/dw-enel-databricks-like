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
    """Return CSS variables for the selected visual mode."""
    if mode == "dark":
        return {
            "--enel-bg": "#0F1115",
            "--enel-bg-soft": "#171A20",
            "--enel-surface": "#1D2128",
            "--enel-surface-2": "#252A32",
            "--enel-text": "#F4F5F7",
            "--enel-muted": "#BAC1CA",
            "--enel-border": "#3A414C",
            "--enel-shadow": "0 14px 34px rgba(0, 0, 0, 0.34)",
        }
    return {
        "--enel-bg": "#F5F6F8",
        "--enel-bg-soft": "#ECEFF3",
        "--enel-surface": "#FFFFFF",
        "--enel-surface-2": "#F0F2F5",
        "--enel-text": "#1C2026",
        "--enel-muted": "#5B6470",
        "--enel-border": "#D8DDE5",
        "--enel-shadow": "0 12px 28px rgba(31, 36, 43, 0.10)",
    }


def dashboard_css(mode: ThemeMode = "light") -> str:
    """Build Streamlit CSS with ENEL hierarchy, animation and accessible contrast."""
    variables = "\n".join(f"{key}: {value};" for key, value in css_variables(mode).items())
    dark = mode == "dark"
    glass_bg = "rgba(29, 33, 40, 0.90)" if dark else "rgba(255, 255, 255, 0.92)"
    glass_border = "rgba(255, 255, 255, 0.14)" if dark else "rgba(28, 32, 38, 0.10)"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

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
}}

html, body, [class*="css"] {{
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-feature-settings: 'cv11', 'ss01';
}}

h1, h2, h3, [data-testid="stMetricValue"] {{
  font-family: 'Inter Tight', 'Inter', system-ui, -apple-system, sans-serif;
}}

code, pre, [data-testid="stMetricValue"], .enel-mono {{
  font-family: 'JetBrains Mono', 'Menlo', monospace;
  font-variant-numeric: tabular-nums;
}}

.stApp {{
  background: var(--enel-bg);
  color: var(--enel-text);
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
  border-radius: var(--enel-radius-lg);
  box-shadow: var(--enel-shadow);
  padding: 1.15rem 1.2rem;
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
  transition: transform 220ms cubic-bezier(.2,.8,.2,1),
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
  color: var(--enel-muted);
}}
[data-testid="stMetricValue"] {{
  font-size: 1.55rem !important;
  font-weight: 700 !important;
  letter-spacing: 0;
  color: var(--enel-text) !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.82rem; font-weight: 600; }}

/* ===== Operational header ===== */
.enel-hero {{
  position: relative;
  overflow: hidden;
  border-radius: var(--enel-radius-lg);
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.2rem;
  color: var(--enel-text);
  background: var(--enel-surface);
  border: 1px solid var(--enel-border);
  border-left: 5px solid var(--enel-secondary);
  box-shadow: var(--enel-shadow);
}}
.enel-hero h1 {{
  position: relative; z-index: 1;
  font-size: clamp(1.65rem, 3vw, 2.35rem);
  line-height: 1.03;
  letter-spacing: 0;
  margin: 0 0 0.45rem;
  font-weight: 800;
  color: var(--enel-text) !important;
}}
.enel-hero p {{
  position: relative; z-index: 1;
  max-width: 880px;
  margin: 0;
  color: var(--enel-muted) !important;
  font-size: 0.98rem;
  line-height: 1.5;
}}
.enel-hero .enel-hero-meta {{
  position: relative; z-index: 1;
  display: inline-flex; gap: 0.5rem; align-items: center;
  margin-top: 0.85rem;
  padding: 0.42rem 0.72rem;
  background: color-mix(in srgb, var(--enel-secondary) 10%, var(--enel-surface) 90%);
  border-radius: var(--enel-radius-sm);
  font-weight: 700; font-size: 0.85rem;
  border: 1px solid color-mix(in srgb, var(--enel-secondary) 24%, var(--enel-border) 76%);
  color: var(--enel-text) !important;
}}

/* ===== Intro / chips ===== */
.enel-intro {{
  border-left: 4px solid var(--enel-secondary);
  background: color-mix(in srgb, var(--enel-surface) 90%, var(--enel-secondary) 10%);
  border-radius: var(--enel-radius-lg);
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
  border-radius: var(--enel-radius-sm);
  border: 1px solid var(--enel-border);
  background: var(--enel-glass-bg);
  color: var(--enel-text);
  font-size: 0.84rem;
  font-weight: 600;
  backdrop-filter: blur(8px);
  transition: transform 160ms ease, border-color 160ms ease;
}}
.enel-chip:hover {{
  transform: translateY(-1px);
  border-color: var(--enel-accent);
}}

.enel-empty {{
  border: 1px dashed var(--enel-border);
  background: var(--enel-glass-bg);
  border-radius: var(--enel-radius-lg);
  padding: 1.6rem;
  color: var(--enel-muted);
  text-align: center;
  backdrop-filter: blur(8px);
}}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {{
  gap: 0.4rem;
  border-bottom: 1px solid var(--enel-border);
  padding-bottom: 0.2rem;
}}
.stTabs [data-baseweb="tab"] {{
  height: 48px;
  background: transparent;
  border-radius: var(--enel-radius-md) var(--enel-radius-md) 0 0;
  padding: 0 1.1rem;
  font-weight: 600;
  color: var(--enel-muted);
  transition: color 180ms ease, background 180ms ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: var(--enel-primary);
  background: color-mix(in srgb, var(--enel-surface) 68%, var(--enel-secondary) 10%);
}}
.stTabs [aria-selected="true"] {{
  color: var(--enel-primary) !important;
  background: var(--enel-glass-bg) !important;
  border-bottom: 3px solid var(--enel-secondary) !important;
}}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {{
  background: var(--enel-glass-bg);
  backdrop-filter: blur(18px) saturate(140%);
  border-right: 1px solid var(--enel-glass-border);
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
  margin-bottom: 0.25rem;
}}
.sidebar-brand {{
  border-bottom: 1px solid var(--enel-border);
  margin: 0 0 0.95rem;
  padding: 0.25rem 0 0.9rem;
}}
.sidebar-brand .eyebrow,
.sb-section .eyebrow {{
  color: var(--enel-muted);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.sidebar-brand strong {{
  display: block;
  color: var(--enel-text);
  font-family: 'Inter Tight', 'Inter', sans-serif;
  font-size: 1.05rem;
  line-height: 1.2;
  margin-top: 0.2rem;
}}
.sidebar-brand span {{
  color: var(--enel-muted);
  display: block;
  font-size: 0.82rem;
  line-height: 1.45;
  margin-top: 0.25rem;
}}
.sb-section {{
  align-items: center;
  border-top: 1px solid var(--enel-border);
  display: flex;
  justify-content: space-between;
  margin: 1rem 0 0.4rem;
  padding-top: 0.8rem;
}}
.sb-section .badge {{
  border: 1px solid var(--enel-border);
  border-radius: var(--enel-radius-sm);
  color: var(--enel-muted);
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.14rem 0.42rem;
}}

/* ===== Plotly fade-in ===== */
.js-plotly-plot {{
  animation: enelFade 320ms cubic-bezier(.2,.8,.2,1) both;
}}
@keyframes enelFade {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* ===== Dataframe polish ===== */
[data-testid="stDataFrame"] {{
  border-radius: var(--enel-radius-md);
  overflow: hidden;
  border: 1px solid var(--enel-border);
}}

/* ===== Buttons ===== */
.stButton > button {{
  border-radius: 8px !important;
  border: 1px solid var(--enel-border) !important;
  background: var(--enel-surface) !important;
  color: var(--enel-text) !important;
  font-weight: 600;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}}
.stButton > button p,
.stButton > button span {{
  color: var(--enel-text) !important;
}}
.stButton > button:hover {{
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--enel-surface) 88%, var(--enel-secondary) 12%)
    !important;
  color: var(--enel-text) !important;
  border-color: var(--enel-secondary) !important;
  box-shadow: 0 8px 18px rgba(200, 16, 46, 0.18);
}}
.stButton > button:focus-visible {{
  outline: 3px solid color-mix(in srgb, var(--enel-secondary) 34%, transparent 66%)
    !important;
  outline-offset: 2px !important;
}}
.stButton > button:disabled,
.stButton > button[disabled] {{
  background: var(--enel-surface-2) !important;
  color: var(--enel-muted) !important;
  border-color: var(--enel-border) !important;
  opacity: 0.76 !important;
}}

/* ===== Streamlit/BaseWeb contrast hardening ===== */
.stApp, .stMarkdown, .stText, .stCaption, .stDataFrame, label, p, li, span {{
  color: var(--enel-text);
}}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] label {{
  color: var(--enel-text);
}}
[data-baseweb="select"] > div,
[data-baseweb="popover"] div,
[data-baseweb="menu"] ul,
[data-testid="stDateInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stChatInput"] textarea {{
  background-color: var(--enel-surface) !important;
  color: var(--enel-text) !important;
  border-color: var(--enel-border) !important;
}}
[data-baseweb="checkbox"] div,
[data-testid="stCheckbox"] div,
[data-testid="stToggle"] div {{
  color: var(--enel-text) !important;
}}
[data-baseweb="checkbox"] [role="checkbox"],
[data-testid="stCheckbox"] [role="checkbox"],
[data-testid="stToggle"] [role="checkbox"] {{
  background-color: var(--enel-surface-2) !important;
  border-color: var(--enel-border) !important;
}}
[data-baseweb="checkbox"] [aria-checked="true"],
[data-testid="stCheckbox"] [aria-checked="true"],
[data-testid="stToggle"] [aria-checked="true"] {{
  background-color: var(--enel-secondary) !important;
  border-color: var(--enel-secondary) !important;
}}
[data-baseweb="tag"] {{
  background-color: color-mix(in srgb, var(--enel-secondary) 14%, var(--enel-surface) 86%)
    !important;
  color: var(--enel-text) !important;
}}
[data-testid="stAlert"] {{
  background: var(--enel-surface) !important;
  color: var(--enel-text) !important;
  border: 1px solid var(--enel-border) !important;
}}
a {{
  color: var(--enel-secondary);
}}
a:hover {{
  color: var(--enel-primary);
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
