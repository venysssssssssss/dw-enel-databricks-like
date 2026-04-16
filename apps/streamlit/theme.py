"""Theme primitives for the ENEL Streamlit dashboards."""

from __future__ import annotations

from typing import Literal

ThemeMode = Literal["light", "dark"]

PALETTE = {
    "primary": "#0F4C81",
    "primary_dark": "#0B3A63",
    "primary_light": "#1F6FB2",
    "secondary": "#00813E",
    "secondary_light": "#2BA65E",
    "accent": "#F7941D",
    "accent_soft": "#FBB040",
    "warning": "#E4002B",
    "neutral_950": "#0C1420",
    "neutral_900": "#1A1A1A",
    "neutral_700": "#3F4A55",
    "neutral_500": "#6B7680",
    "neutral_200": "#E6ECF2",
    "neutral_100": "#EDF3F8",
    "neutral_50": "#F6F9FC",
    "surface": "#FFFFFF",
    "ce": "#F7941D",
    "sp": "#0F4C81",
    "muted": "#6B7680",
}

CATEGORICAL_SEQUENCE = [
    "#0F4C81",
    "#F7941D",
    "#00813E",
    "#5C2D91",
    "#E4002B",
    "#1F6FB2",
    "#FBB040",
    "#2BA65E",
]

SEQUENTIAL_BLUE = [
    "#EAF2FA",
    "#C7DDF0",
    "#9EC4E3",
    "#6FA6D3",
    "#4088C0",
    "#1F6FB2",
    "#0F4C81",
    "#0B3A63",
]

SEQUENTIAL_ORANGE = [
    "#FFF3E0",
    "#FFD9A6",
    "#FBB040",
    "#F7941D",
    "#E07B10",
    "#B86008",
]

SEQUENTIAL_GREEN = [
    "#E6F4EC",
    "#B6E0C5",
    "#80C89C",
    "#2BA65E",
    "#00813E",
    "#005F2C",
]


def css_variables(mode: ThemeMode = "light") -> dict[str, str]:
    """Return CSS variables for the selected visual mode."""
    if mode == "dark":
        return {
            "--enel-bg": "#07111F",
            "--enel-bg-soft": "#0D1D30",
            "--enel-surface": "#12243A",
            "--enel-surface-2": "#18324F",
            "--enel-text": "#F4F8FC",
            "--enel-muted": "#A9B8C8",
            "--enel-border": "#294461",
            "--enel-shadow": "0 18px 45px rgba(0, 0, 0, 0.38)",
        }
    return {
        "--enel-bg": "#F4F8FC",
        "--enel-bg-soft": "#EAF2FA",
        "--enel-surface": "#FFFFFF",
        "--enel-surface-2": "#F6F9FC",
        "--enel-text": "#172230",
        "--enel-muted": "#596879",
        "--enel-border": "#DCE7F1",
        "--enel-shadow": "0 18px 45px rgba(15, 76, 129, 0.10)",
    }


def dashboard_css(mode: ThemeMode = "light") -> str:
    """Build Streamlit CSS with ENEL hierarchy, animation and accessible contrast."""
    variables = "\n".join(f"{key}: {value};" for key, value in css_variables(mode).items())
    dark = mode == "dark"
    glass_bg = "rgba(18, 36, 58, 0.62)" if dark else "rgba(255, 255, 255, 0.72)"
    glass_border = "rgba(255, 255, 255, 0.08)" if dark else "rgba(15, 76, 129, 0.10)"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
  {variables}
  --enel-primary: {PALETTE["primary"]};
  --enel-primary-light: {PALETTE["primary_light"]};
  --enel-secondary: {PALETTE["secondary"]};
  --enel-accent: {PALETTE["accent"]};
  --enel-warning: {PALETTE["warning"]};
  --enel-glass-bg: {glass_bg};
  --enel-glass-border: {glass_border};
  --enel-radius-lg: 22px;
  --enel-radius-md: 14px;
  --enel-radius-sm: 10px;
}}

html, body, [class*="css"] {{
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-feature-settings: 'cv11', 'ss01';
}}

code, pre, [data-testid="stMetricValue"], .enel-mono {{
  font-family: 'JetBrains Mono', 'Menlo', monospace;
  font-variant-numeric: tabular-nums;
}}

.stApp {{
  background:
    radial-gradient(circle at top left, rgba(247, 148, 29, 0.14), transparent 32rem),
    radial-gradient(circle at top right, rgba(15, 76, 129, 0.18), transparent 30rem),
    radial-gradient(circle at bottom right, rgba(0, 129, 62, 0.10), transparent 26rem),
    linear-gradient(180deg, var(--enel-bg) 0%, var(--enel-bg-soft) 100%);
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
  border-color: rgba(247, 148, 29, 0.55);
  box-shadow: 0 28px 65px rgba(15, 76, 129, 0.18);
}}
[data-testid="stMetricLabel"] p {{
  font-size: 0.78rem; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--enel-muted);
}}
[data-testid="stMetricValue"] {{
  font-size: 1.55rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em;
  color: var(--enel-text) !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.82rem; font-weight: 600; }}

/* ===== Hero ===== */
.enel-hero {{
  position: relative;
  overflow: hidden;
  border-radius: 30px;
  padding: 2.1rem 2.2rem;
  margin-bottom: 1.2rem;
  color: #FFFFFF;
  background:
    linear-gradient(135deg, rgba(15,76,129,0.98), rgba(0,129,62,0.88)),
    radial-gradient(circle at 88% 12%, rgba(247,148,29,0.72), transparent 18rem),
    radial-gradient(circle at 8% 88%, rgba(228,0,43,0.32), transparent 16rem);
  box-shadow: 0 28px 80px rgba(15, 76, 129, 0.26);
}}
.enel-hero::after {{
  content: ""; position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none; opacity: 0.5;
}}
.enel-hero h1 {{
  position: relative; z-index: 1;
  font-size: clamp(2.15rem, 4vw, 3.6rem);
  line-height: 0.98;
  letter-spacing: -0.05em;
  margin: 0 0 0.7rem;
  font-weight: 800;
}}
.enel-hero p {{
  position: relative; z-index: 1;
  max-width: 880px;
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  font-size: 1.05rem;
  line-height: 1.55;
}}
.enel-hero .enel-hero-meta {{
  position: relative; z-index: 1;
  display: inline-flex; gap: 0.5rem; align-items: center;
  margin-top: 1rem;
  padding: 0.45rem 0.85rem;
  background: rgba(255,255,255,0.14);
  backdrop-filter: blur(14px);
  border-radius: 999px;
  font-weight: 700; font-size: 0.85rem;
  border: 1px solid rgba(255,255,255,0.22);
}}

/* ===== Intro / chips ===== */
.enel-intro {{
  border-left: 5px solid var(--enel-accent);
  background: color-mix(in srgb, var(--enel-surface) 88%, var(--enel-accent) 12%);
  border-radius: 18px;
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
  border-radius: 999px;
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
  border-radius: 22px;
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
  border-radius: 12px 12px 0 0;
  padding: 0 1.1rem;
  font-weight: 600;
  color: var(--enel-muted);
  transition: color 180ms ease, background 180ms ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: var(--enel-primary);
  background: color-mix(in srgb, var(--enel-surface) 60%, var(--enel-accent) 8%);
}}
.stTabs [aria-selected="true"] {{
  color: var(--enel-primary) !important;
  background: var(--enel-glass-bg) !important;
  border-bottom: 3px solid var(--enel-accent) !important;
}}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {{
  background: var(--enel-glass-bg);
  backdrop-filter: blur(18px) saturate(140%);
  border-right: 1px solid var(--enel-glass-border);
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
  border-radius: 12px;
  border: 1px solid var(--enel-border);
  font-weight: 600;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}}
.stButton > button:hover {{
  transform: translateY(-1px);
  border-color: var(--enel-accent);
  box-shadow: 0 8px 18px rgba(247, 148, 29, 0.18);
}}
</style>
"""


def plotly_template(mode: ThemeMode = "light") -> dict[str, object]:
    """Small Plotly layout template shared across layers."""
    dark = mode == "dark"
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, sans-serif", "color": "#F4F8FC" if dark else "#172230"},
        "margin": {"l": 24, "r": 24, "t": 48, "b": 32},
        "hoverlabel": {"bgcolor": "#12243A" if dark else "#FFFFFF", "font_size": 13},
    }


def format_int(value: int | float) -> str:
    """Format integers for pt-BR dashboard cards."""
    return f"{int(value):,}".replace(",", ".")


def format_pct(value: float, *, scale: float = 100.0, digits: int = 1) -> str:
    """Format percentages where source values usually come as 0..1 rates."""
    return f"{value * scale:.{digits}f}%"
