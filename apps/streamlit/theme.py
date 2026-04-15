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
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  {variables}
  --enel-primary: {PALETTE["primary"]};
  --enel-primary-light: {PALETTE["primary_light"]};
  --enel-secondary: {PALETTE["secondary"]};
  --enel-accent: {PALETTE["accent"]};
  --enel-warning: {PALETTE["warning"]};
}}

html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
}}

.stApp {{
  background:
    radial-gradient(circle at top left, rgba(247, 148, 29, 0.15), transparent 30rem),
    radial-gradient(circle at top right, rgba(15, 76, 129, 0.18), transparent 28rem),
    linear-gradient(180deg, var(--enel-bg) 0%, var(--enel-bg-soft) 100%);
  color: var(--enel-text);
}}

.block-container {{
  padding-top: 1.4rem;
  max-width: 1480px;
}}

[data-testid="stMetric"], .enel-card {{
  background: linear-gradient(145deg, var(--enel-surface), var(--enel-surface-2));
  border: 1px solid var(--enel-border);
  border-radius: 22px;
  box-shadow: var(--enel-shadow);
  padding: 1.1rem;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}}

[data-testid="stMetric"]:hover, .enel-card:hover {{
  transform: translateY(-2px);
  border-color: rgba(247, 148, 29, 0.55);
  box-shadow: 0 22px 55px rgba(15, 76, 129, 0.16);
}}

.enel-hero {{
  position: relative;
  overflow: hidden;
  border-radius: 30px;
  padding: 2rem;
  margin-bottom: 1.2rem;
  color: #FFFFFF;
  background:
    linear-gradient(135deg, rgba(15,76,129,0.98), rgba(0,129,62,0.88)),
    radial-gradient(circle at 88% 12%, rgba(247,148,29,0.72), transparent 18rem);
  box-shadow: 0 28px 80px rgba(15, 76, 129, 0.26);
}}

.enel-hero h1 {{
  font-size: clamp(2.15rem, 4vw, 4rem);
  line-height: 0.96;
  letter-spacing: -0.06em;
  margin: 0 0 0.8rem;
  font-weight: 800;
}}

.enel-hero p {{
  max-width: 880px;
  margin: 0;
  color: rgba(255, 255, 255, 0.88);
  font-size: 1.05rem;
}}

.enel-intro {{
  border-left: 5px solid var(--enel-accent);
  background: color-mix(in srgb, var(--enel-surface) 86%, var(--enel-accent) 14%);
  border-radius: 18px;
  padding: 1rem 1.2rem;
  margin: 0.25rem 0 1rem;
}}

.enel-intro strong {{
  color: var(--enel-primary);
}}

.enel-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  margin: 0 0.35rem 0.35rem 0;
  border-radius: 999px;
  border: 1px solid var(--enel-border);
  background: var(--enel-surface);
  color: var(--enel-text);
  font-size: 0.84rem;
  font-weight: 600;
}}

.enel-empty {{
  border: 1px dashed var(--enel-border);
  background: var(--enel-surface);
  border-radius: 22px;
  padding: 1.4rem;
  color: var(--enel-muted);
}}

.js-plotly-plot {{
  animation: enelFade 220ms ease-out;
}}

@keyframes enelFade {{
  from {{ opacity: 0; transform: translateY(4px); }}
  to {{ opacity: 1; transform: translateY(0); }}
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
