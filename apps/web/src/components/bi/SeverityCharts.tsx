import { useEffect, useRef, useState } from "react";
import { formatCausa } from "../../lib/analytics";

type TTState = { html: string; x: number; y: number; on: boolean };
const initialTT: TTState = { html: "", x: 0, y: 0, on: false };

export const fmtN = (n: number): string => Number(n || 0).toLocaleString("pt-BR");
export const fmtMoney = (n: number): string =>
  "R$ " +
  Number(n || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
export const fmtPct = (n: number): string =>
  (Number(n || 0)).toFixed(1).replace(".", ",") + "%";

function useContainerWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T | null>(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    if (!ref.current) return;
    const obs = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) setW(Math.max(320, Math.floor(cr.width)));
    });
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return { ref, width: w };
}

function Tooltip({ state }: { state: TTState }) {
  return (
    <div
      className={"sev-tt" + (state.on ? " is-on" : "")}
      style={{ left: state.x + 14, top: state.y + 14 }}
      role="tooltip"
      dangerouslySetInnerHTML={{ __html: state.html }}
    />
  );
}

/* ──────────────────────────────────────
 * Volume bars — monthly series
 * ────────────────────────────────────── */
export function VolumeBarsChart({
  months,
  values,
  sevLabel,
  height = 320
}: {
  months: string[];
  values: number[];
  sevLabel: string;
  height?: number;
}) {
  const { ref, width: W } = useContainerWidth<HTMLDivElement>(720);
  const [tt, setTt] = useState(initialTT);
  const H = height;
  const M = { t: 24, r: 16, b: 40, l: 52 };
  const iw = Math.max(200, W - M.l - M.r);
  const ih = H - M.t - M.b;
  const max = Math.max(1, ...values);
  const yMax = Math.max(50, Math.ceil(max / 50) * 50 + 50);
  const bw = values.length ? (iw / values.length) * 0.64 : 0;
  const gap = values.length ? (iw / values.length) * 0.36 : 0;

  return (
    <div ref={ref} className="sev-chart-wrap">
      <svg className="sev-chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Volume mensal · ${sevLabel}`}>
        <defs>
          <linearGradient id="sevBarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sev-primary)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--sev-secondary)" stopOpacity="0.70" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((p) => {
          const v = yMax * p;
          const y = M.t + ih - (v / yMax) * ih;
          return (
            <g key={p}>
              <line className="sev-grid" x1={M.l} x2={W - M.r} y1={y} y2={y} />
              <text className="sev-axis" x={M.l - 8} y={y + 3} textAnchor="end">
                {fmtN(Math.round(v))}
              </text>
            </g>
          );
        })}
        {values.map((v, i) => {
          const bh = (v / yMax) * ih;
          const x = M.l + i * (bw + gap) + gap / 2;
          const y = M.t + ih - bh;
          return (
            <g key={i}>
              <rect
                className="sev-bar"
                x={x}
                y={y}
                width={bw}
                height={Math.max(0, bh)}
                rx={3}
                fill="url(#sevBarGrad)"
                onMouseMove={(e) =>
                  setTt({
                    on: true,
                    x: e.clientX,
                    y: e.clientY,
                    html: `<div class="tt-label">${months[i]} · ${sevLabel}</div><div class="tt-val">${fmtN(v)}</div><div class="tt-row"><span>reclamações no mês</span></div>`
                  })
                }
                onMouseLeave={() => setTt((t) => ({ ...t, on: false }))}
              />
              <text className="sev-bar-label" x={x + bw / 2} y={y - 6} textAnchor="middle">
                {fmtN(v)}
              </text>
            </g>
          );
        })}
        {months.map((m, i) => {
          const x = M.l + i * (bw + gap) + gap / 2 + bw / 2;
          return (
            <text key={m + i} className="sev-axis" x={x} y={H - M.b + 18} textAnchor="middle">
              {m}
            </text>
          );
        })}
        <line className="sev-axis-line" x1={M.l} x2={W - M.r} y1={M.t + ih} y2={M.t + ih} />
      </svg>
      <Tooltip state={tt} />
    </div>
  );
}

/* ──────────────────────────────────────
 * Horizontal bars — categorias
 * ────────────────────────────────────── */
export type Categoria = { categoria_id: string; categoria: string; vol: number; pct: number };

export function CategoriasHBars({
  rows,
  activeId,
  onToggle
}: {
  rows: Categoria[];
  activeId: string | null;
  onToggle: (id: string) => void;
}) {
  const [tt, setTt] = useState(initialTT);
  const max = Math.max(1, ...rows.map((r) => r.vol));
  return (
    <div className="sev-hbar-list">
      {rows.map((c) => {
        const w = (c.vol / max) * 100;
        const active = activeId === c.categoria_id;
        return (
          <button
            type="button"
            key={c.categoria_id}
            className={"sev-hbar-row" + (active ? " is-active" : "")}
            onClick={() => onToggle(c.categoria_id)}
            onMouseMove={(e) =>
              setTt({
                on: true,
                x: e.clientX,
                y: e.clientY,
                html: `<div class="tt-label">${c.categoria}</div><div class="tt-val">${fmtN(c.vol)}</div><div class="tt-row"><span>% do total</span><b>${c.pct.toFixed(1)}%</b></div>`
              })
            }
            onMouseLeave={() => setTt((t) => ({ ...t, on: false }))}
          >
            <span className="sev-hbar-name" title={c.categoria}>
              {c.categoria}
            </span>
            <span className="sev-hbar-track">
              <span className="sev-hbar-fill" style={{ width: `${w}%` }} />
            </span>
            <span className="sev-hbar-val">{fmtN(c.vol)}</span>
            <span className="sev-hbar-pct">{c.pct.toFixed(1)}%</span>
          </button>
        );
      })}
      <Tooltip state={tt} />
    </div>
  );
}

/* ──────────────────────────────────────
 * Scatter — causas canônicas
 * ────────────────────────────────────── */
export type Causa = {
  id: string;
  nome: string;
  vol: number;
  proc: number;
  reinc: number;
  cat: string;
};

const CAT_COLORS: Record<string, string> = {
  operacional: "var(--terra)",
  estimativa: "var(--amber-deep, var(--terra-deep))",
  medidor: "var(--plum)",
  cadastral: "var(--sage)",
  tarifa: "var(--ocean, var(--terra-deep))",
  fraude: "var(--wine, var(--plum))",
  faturamento: "var(--terra-deep)",
  juridico: "var(--plum-deep)",
  contestacao_cliente: "var(--terra)",
  nao_classificada: "var(--ink-faint)"
};

export function CausasScatter({
  rows,
  activeId,
  onToggle,
  height = 360
}: {
  rows: Causa[];
  activeId: string | null;
  onToggle: (id: string) => void;
  height?: number;
}) {
  const { ref, width: W } = useContainerWidth<HTMLDivElement>(720);
  const [tt, setTt] = useState(initialTT);
  const H = height;
  const M = { t: 20, r: 24, b: 52, l: 56 };
  const iw = Math.max(200, W - M.l - M.r);
  const ih = H - M.t - M.b;
  const xMax = Math.max(1, ...rows.map((c) => c.vol));
  const xMaxRound = Math.max(100, Math.ceil(xMax / 100) * 100);
  const rMax = Math.max(1, ...rows.map((c) => c.reinc));
  const midX = M.l + iw / 2;
  const midY = M.t + ih / 2;
  const cats = Array.from(new Set(rows.map((r) => r.cat))).filter(Boolean);

  return (
    <div ref={ref} className="sev-chart-wrap">
      <svg className="sev-chart-svg sev-scatter" viewBox={`0 0 ${W} ${H}`}>
        {[0, 25, 50, 75, 100].map((p) => {
          const y = M.t + ih - (p / 100) * ih;
          return (
            <g key={p}>
              <line className="sev-grid" x1={M.l} x2={W - M.r} y1={y} y2={y} />
              <text className="sev-axis" x={M.l - 8} y={y + 3} textAnchor="end">
                {p}%
              </text>
            </g>
          );
        })}
        {Array.from({ length: 6 }, (_, i) => {
          const v = (xMaxRound / 5) * i;
          const x = M.l + (v / xMaxRound) * iw;
          return (
            <text key={i} className="sev-axis" x={x} y={H - M.b + 18} textAnchor="middle">
              {fmtN(Math.round(v))}
            </text>
          );
        })}
        <line className="sev-grid" x1={midX} x2={midX} y1={M.t} y2={M.t + ih} strokeDasharray="1 4" opacity={0.6} />
        <line className="sev-grid" x1={M.l} x2={W - M.r} y1={midY} y2={midY} strokeDasharray="1 4" opacity={0.6} />
        <text className="sev-quadrant" x={W - M.r - 4} y={M.t + 14} textAnchor="end">
          alto vol · alta proc.
        </text>
        <text className="sev-quadrant" x={M.l + 4} y={M.t + 14}>
          baixo vol · alta proc.
        </text>
        <text className="sev-quadrant" x={W - M.r - 4} y={M.t + ih - 6} textAnchor="end">
          alto vol · baixa proc.
        </text>
        <text className="sev-quadrant" x={M.l + 4} y={M.t + ih - 6}>
          baixo vol · baixa proc.
        </text>
        <line className="sev-axis-line" x1={M.l} x2={W - M.r} y1={M.t + ih} y2={M.t + ih} />
        <line className="sev-axis-line" x1={M.l} x2={M.l} y1={M.t} y2={M.t + ih} />
        <text
          className="sev-axis"
          x={M.l - 40}
          y={M.t + ih / 2}
          transform={`rotate(-90, ${M.l - 40}, ${M.t + ih / 2})`}
          textAnchor="middle"
        >
          % procedência →
        </text>
        <text className="sev-axis" x={M.l + iw / 2} y={H - 6} textAnchor="middle">
          volume de ordens →
        </text>
        {rows.map((c) => {
          const cx = M.l + (c.vol / xMaxRound) * iw;
          const cy = M.t + ih - (c.proc / 100) * ih;
          const r = 6 + (c.reinc / rMax) * 22;
          const active = activeId === c.id;
          const color = CAT_COLORS[c.cat] || "var(--sev-primary)";
          const friendly = formatCausa(c.nome);
          const label = friendly.length > 22 ? friendly.slice(0, 22) + "…" : friendly;
          return (
            <g key={c.id}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={color}
                fillOpacity={active ? 0.9 : 0.52}
                stroke={color}
                strokeWidth={active ? 2 : 1.25}
                onMouseMove={(e) =>
                  setTt({
                    on: true,
                    x: e.clientX,
                    y: e.clientY,
                    html: `<div class="tt-label">causa canônica</div><div class="tt-val">${friendly}</div><div class="tt-row"><span>id</span><b>${c.nome}</b></div><div class="tt-row"><span>volume</span><b>${fmtN(c.vol)}</b></div><div class="tt-row"><span>procedência</span><b>${c.proc.toFixed(1)}%</b></div><div class="tt-row"><span>reincidências</span><b>${fmtN(c.reinc)}</b></div><div class="tt-row"><span>categoria</span><b>${c.cat}</b></div>`
                  })
                }
                onMouseLeave={() => setTt((t) => ({ ...t, on: false }))}
                onClick={() => onToggle(c.id)}
                style={{ cursor: "pointer" }}
              />
              <text x={cx} y={cy - r - 5} textAnchor="middle" className="sev-scatter-label">
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="sev-scatter-legend">
        {cats.map((cat) => (
          <span key={cat}>
            <span className="dot" style={{ background: CAT_COLORS[cat] || "var(--sev-primary)" }} />
            {cat}
          </span>
        ))}
        <span style={{ marginLeft: 12, color: "var(--ink-faint)" }}>tamanho = reincidências</span>
      </div>
      <Tooltip state={tt} />
    </div>
  );
}

/* ──────────────────────────────────────
 * Sparkline — inline SVG
 * ────────────────────────────────────── */
export function Sparkline({ values, w = 70, h = 18 }: { values: number[]; w?: number; h?: number }) {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const d = values
    .map((v, i) => {
      const x = (i / (values.length - 1 || 1)) * w;
      const y = h - ((v - min) / range) * h;
      return (i === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1);
    })
    .join(" ");
  const lx = w;
  const ly = h - ((values[values.length - 1] - min) / range) * h;
  return (
    <svg className="sev-spark" viewBox={`0 0 ${w} ${h}`}>
      <path d={d} />
      <circle cx={lx.toFixed(1)} cy={ly.toFixed(1)} r={2} />
    </svg>
  );
}
