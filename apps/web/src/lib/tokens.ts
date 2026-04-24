/**
 * Design tokens — hybrid system:
 * - graphite: chat, dense surfaces (Refactor.html).
 * - aconchegante: BI/MIS executive (MIS BI Aconchegante.html).
 *
 * Runtime selection via data-surface="graphite" | "aconchegante" on <main>.
 */

export const tokens = {
  brand: {
    enelWine: "#870A3C",
    enelRed: "#C8102E",
    enelSignal: "#E4002B"
  },
  graphite: {
    accent: "oklch(58% 0.19 15)",
    bg: "oklch(17% 0.006 260)",
    surface: "oklch(20% 0.006 260)"
  },
  aconchegante: {
    terra: "oklch(60% 0.17 28)",
    plum: "oklch(36% 0.14 12)",
    paper: "oklch(97.2% 0.012 60)",
    card: "oklch(99% 0.006 60)"
  },
  status: {
    ok: "oklch(60% 0.14 150)",
    warn: "oklch(74% 0.14 70)",
    crit: "oklch(64% 0.20 25)"
  },
  font: {
    display: "'Inter Tight', 'Inter', system-ui, sans-serif",
    body: "'Inter', system-ui, sans-serif",
    serif: "'Fraunces', Georgia, serif",
    mono: "'JetBrains Mono', ui-monospace, monospace"
  }
} as const;

export const chartPalette = [
  "oklch(60% 0.17 28)",   // terra
  "oklch(36% 0.14 12)",   // plum
  "oklch(74% 0.14 70)",   // amber
  "oklch(58% 0.09 145)",  // sage
  "oklch(52% 0.11 220)"   // ocean
];
