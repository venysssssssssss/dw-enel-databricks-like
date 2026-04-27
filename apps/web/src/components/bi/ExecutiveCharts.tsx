import { useEffect, useId, useRef, useState } from "react";
import {
  formatNumber,
  formatPercent,
  type ScatterPoint,
  type SeverityBucket,
  type Severity
} from "../../lib/analytics";

type TooltipState = { html: string; x: number; y: number; on: boolean };
const initialTT: TooltipState = { html: "", x: 0, y: 0, on: false };

const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "var(--plum-deep, oklch(28% 0.12 10))",
  high: "var(--terra-deep, oklch(48% 0.17 24))",
  medium: "var(--amber, oklch(74% 0.15 70))",
  low: "var(--sage, oklch(58% 0.09 145))"
};

const SCATTER_PALETTE = [
  "var(--terra)",
  "var(--plum)",
  "var(--amber-deep, var(--amber))",
  "var(--sage)",
  "var(--ocean, var(--terra-deep))",
  "var(--wine, var(--plum-deep))"
];

function useContainerWidth<T extends HTMLElement>(fallback = 640): {
  ref: React.MutableRefObject<T | null>;
  width: number;
} {
  const ref = useRef<T | null>(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    if (!ref.current) return;
    const obs = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) setW(Math.max(280, Math.floor(cr.width)));
    });
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return { ref, width: w };
}

function FloatingTooltip({ state }: { state: TooltipState }) {
  return (
    <div
      className={"sev-tt" + (state.on ? " is-on" : "")}
      style={{ left: state.x + 14, top: state.y + 14 }}
      role="tooltip"
      dangerouslySetInnerHTML={{ __html: state.html }}
    />
  );
}

/* ──────────────────────────────────────────────────────────────────
 * Donut — distribuição por severidade
 * ────────────────────────────────────────────────────────────────── */
export function SeverityDonut({
  buckets,
  height = 280,
  emptyHint
}: {
  buckets: SeverityBucket[];
  height?: number;
  emptyHint?: string;
}) {
  const total = buckets.reduce((sum, b) => sum + b.value, 0);
  const { ref, width } = useContainerWidth<HTMLDivElement>(360);
  const [tt, setTt] = useState(initialTT);
  const id = useId();

  if (total <= 0) {
    return (
      <div className="exec-empty" style={{ minHeight: height }}>
        <div className="exec-empty-mark" aria-hidden>
          ◯
        </div>
        <p>{emptyHint ?? "Sem volume para distribuir nessa janela de filtros."}</p>
      </div>
    );
  }

  const size = Math.min(height, width);
  const cx = size / 2;
  const cy = size / 2;
  const outer = size * 0.42;
  const inner = size * 0.27;

  let cursor = -Math.PI / 2;
  const arcs = buckets
    .filter((b) => b.value > 0)
    .map((bucket) => {
      const angle = (bucket.value / total) * Math.PI * 2;
      const start = cursor;
      const end = cursor + angle;
      cursor = end;
      const path = donutPath(cx, cy, inner, outer, start, end);
      const midAngle = (start + end) / 2;
      const labelR = (inner + outer) / 2;
      const lx = cx + Math.cos(midAngle) * labelR;
      const ly = cy + Math.sin(midAngle) * labelR;
      return { bucket, path, lx, ly, angle };
    });

  const dominant = arcs.reduce((best, arc) =>
    arc.bucket.value > best.bucket.value ? arc : best,
    arcs[0]
  );

  return (
    <div ref={ref} className="exec-donut">
      <div className="exec-donut-figure" style={{ width: size, height: size }}>
        <svg
          viewBox={`0 0 ${size} ${size}`}
          width={size}
          height={size}
          role="img"
          aria-labelledby={`${id}-title`}
        >
          <title id={`${id}-title`}>Distribuição por severidade</title>
          {arcs.map((arc) => (
            <path
              key={arc.bucket.key}
              d={arc.path}
              fill={SEVERITY_COLOR[arc.bucket.key]}
              stroke="var(--card, var(--surface))"
              strokeWidth={1.4}
              onMouseMove={(event) =>
                setTt({
                  on: true,
                  x: event.clientX,
                  y: event.clientY,
                  html: `<div class="tt-label">${arc.bucket.label}</div><div class="tt-val">${formatNumber(arc.bucket.value)}</div><div class="tt-row"><span>% do total</span><b>${formatPercent(arc.bucket.pct)}</b></div>`
                })
              }
              onMouseLeave={() => setTt((t) => ({ ...t, on: false }))}
            />
          ))}
          {arcs
            .filter((arc) => arc.angle > 0.32)
            .map((arc) => (
              <text
                key={`${arc.bucket.key}-label`}
                x={arc.lx}
                y={arc.ly}
                className="exec-donut-arc-label"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {formatPercent(arc.bucket.pct, 0)}
              </text>
            ))}
          <text
            x={cx}
            y={cy - 8}
            className="exec-donut-center-eyebrow"
            textAnchor="middle"
          >
            Volume total
          </text>
          <text x={cx} y={cy + 18} className="exec-donut-center-value" textAnchor="middle">
            {formatNumber(total)}
          </text>
          {dominant ? (
            <text x={cx} y={cy + 36} className="exec-donut-center-foot" textAnchor="middle">
              líder · {dominant.bucket.label}
            </text>
          ) : null}
        </svg>
      </div>
      <ul className="exec-donut-legend" aria-label="Legenda severidade">
        {buckets.map((bucket) => (
          <li key={bucket.key} data-empty={bucket.value === 0 ? "true" : "false"}>
            <span
              className="dot"
              style={{ background: SEVERITY_COLOR[bucket.key] }}
              aria-hidden
            />
            <span className="lbl">{bucket.label}</span>
            <span className="num">{formatNumber(bucket.value)}</span>
            <span className="pct">{formatPercent(bucket.pct)}</span>
          </li>
        ))}
      </ul>
      <FloatingTooltip state={tt} />
    </div>
  );
}

function donutPath(
  cx: number,
  cy: number,
  inner: number,
  outer: number,
  start: number,
  end: number
): string {
  const large = end - start > Math.PI ? 1 : 0;
  if (Math.abs(end - start - Math.PI * 2) < 1e-6) {
    return [
      `M ${cx + outer} ${cy}`,
      `A ${outer} ${outer} 0 1 1 ${cx - outer} ${cy}`,
      `A ${outer} ${outer} 0 1 1 ${cx + outer} ${cy}`,
      `M ${cx + inner} ${cy}`,
      `A ${inner} ${inner} 0 1 0 ${cx - inner} ${cy}`,
      `A ${inner} ${inner} 0 1 0 ${cx + inner} ${cy}`,
      "Z"
    ].join(" ");
  }
  const x1 = cx + Math.cos(start) * outer;
  const y1 = cy + Math.sin(start) * outer;
  const x2 = cx + Math.cos(end) * outer;
  const y2 = cy + Math.sin(end) * outer;
  const x3 = cx + Math.cos(end) * inner;
  const y3 = cy + Math.sin(end) * inner;
  const x4 = cx + Math.cos(start) * inner;
  const y4 = cy + Math.sin(start) * inner;
  return [
    `M ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    `A ${outer} ${outer} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`,
    `L ${x3.toFixed(2)} ${y3.toFixed(2)}`,
    `A ${inner} ${inner} 0 ${large} 0 ${x4.toFixed(2)} ${y4.toFixed(2)}`,
    "Z"
  ].join(" ");
}

/* ──────────────────────────────────────────────────────────────────
 * Scatter — dispersão geral (volume × refaturamento)
 * ────────────────────────────────────────────────────────────────── */
export function ExecutiveScatter({
  points,
  height = 320,
  xLabel = "volume de ordens",
  yLabel = "% refaturamento",
  emptyHint
}: {
  points: ScatterPoint[];
  height?: number;
  xLabel?: string;
  yLabel?: string;
  emptyHint?: string;
}) {
  const { ref, width } = useContainerWidth<HTMLDivElement>(640);
  const [tt, setTt] = useState(initialTT);

  if (!points.length) {
    return (
      <div className="exec-empty" style={{ minHeight: height }}>
        <div className="exec-empty-mark" aria-hidden>
          ⌖
        </div>
        <p>{emptyHint ?? "Sem causas suficientes para gerar a dispersão."}</p>
      </div>
    );
  }

  const W = width;
  const H = height;
  const M = { t: 22, r: 24, b: 46, l: 56 };
  const iw = Math.max(160, W - M.l - M.r);
  const ih = H - M.t - M.b;
  const xMax = Math.max(1, ...points.map((p) => p.x));
  const xMaxRound = Math.max(50, Math.ceil(xMax / 50) * 50);
  const sizeMax = Math.max(1, ...points.map((p) => p.size));

  const colorFor = (group: string): string => {
    let hash = 0;
    for (let i = 0; i < group.length; i += 1) {
      hash = (hash * 31 + group.charCodeAt(i)) & 0xffffffff;
    }
    return SCATTER_PALETTE[Math.abs(hash) % SCATTER_PALETTE.length];
  };

  const midX = M.l + iw / 2;
  const midY = M.t + ih / 2;

  return (
    <div ref={ref} className="exec-scatter">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Dispersão volume × refaturamento">
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
        {Array.from({ length: 6 }, (_, idx) => {
          const value = (xMaxRound / 5) * idx;
          const x = M.l + (value / xMaxRound) * iw;
          return (
            <text key={idx} className="sev-axis" x={x} y={H - M.b + 18} textAnchor="middle">
              {formatNumber(value)}
            </text>
          );
        })}
        <line
          className="sev-grid"
          x1={midX}
          x2={midX}
          y1={M.t}
          y2={M.t + ih}
          strokeDasharray="1 4"
          opacity={0.55}
        />
        <line
          className="sev-grid"
          x1={M.l}
          x2={W - M.r}
          y1={midY}
          y2={midY}
          strokeDasharray="1 4"
          opacity={0.55}
        />
        <text className="sev-quadrant" x={W - M.r - 4} y={M.t + 14} textAnchor="end">
          alto vol · alto refat
        </text>
        <text className="sev-quadrant" x={M.l + 4} y={M.t + 14}>
          baixo vol · alto refat
        </text>
        <text
          className="sev-quadrant"
          x={W - M.r - 4}
          y={M.t + ih - 6}
          textAnchor="end"
        >
          alto vol · baixo refat
        </text>
        <text className="sev-quadrant" x={M.l + 4} y={M.t + ih - 6}>
          baixo vol · baixo refat
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
          {yLabel} →
        </text>
        <text className="sev-axis" x={M.l + iw / 2} y={H - 6} textAnchor="middle">
          {xLabel} →
        </text>
        {points.map((p) => {
          const cx = M.l + (p.x / xMaxRound) * iw;
          const cy = M.t + ih - (p.y / 100) * ih;
          const r = 5 + (p.size / sizeMax) * 18;
          const color = colorFor(p.group);
          const label = p.label.length > 22 ? p.label.slice(0, 22) + "…" : p.label;
          return (
            <g key={p.id}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={color}
                fillOpacity={0.55}
                stroke={color}
                strokeWidth={1.25}
                onMouseMove={(event) =>
                  setTt({
                    on: true,
                    x: event.clientX,
                    y: event.clientY,
                    html: `<div class="tt-label">${p.label}</div><div class="tt-row"><span>${xLabel}</span><b>${formatNumber(p.x)}</b></div><div class="tt-row"><span>${yLabel}</span><b>${formatPercent(p.y)}</b></div>`
                  })
                }
                onMouseLeave={() => setTt((t) => ({ ...t, on: false }))}
              />
              <text
                x={cx}
                y={cy - r - 5}
                textAnchor="middle"
                className="sev-scatter-label"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      <FloatingTooltip state={tt} />
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
 * Mini bar list — distribuição por categoria/severidade compacta
 * ────────────────────────────────────────────────────────────────── */
export function MiniBarList({
  rows,
  emptyHint,
  maxRows = 6
}: {
  rows: { label: string; value: number; pct: number; color?: string }[];
  emptyHint?: string;
  maxRows?: number;
}) {
  if (!rows.length) {
    return <p className="exec-mini-empty">{emptyHint ?? "Sem dados para exibir."}</p>;
  }
  const max = Math.max(1, ...rows.map((r) => r.value));
  const visible = rows.slice(0, maxRows);
  return (
    <ul className="exec-mini-bars">
      {visible.map((row) => {
        const widthPct = Math.max(2, (row.value / max) * 100);
        return (
          <li key={row.label}>
            <span className="lbl" title={row.label}>
              {row.label}
            </span>
            <span className="track">
              <span
                className="fill"
                style={{
                  width: `${widthPct}%`,
                  background: row.color ?? "var(--terra)"
                }}
              />
            </span>
            <span className="num">{formatNumber(row.value)}</span>
            <span className="pct">{formatPercent(row.pct)}</span>
          </li>
        );
      })}
    </ul>
  );
}

/* ──────────────────────────────────────────────────────────────────
 * Sparkline — série mensal para o card de cobertura do modelo
 * ────────────────────────────────────────────────────────────────── */
export function MonthlySparkline({
  series,
  height = 96
}: {
  series: { label: string; total: number }[];
  height?: number;
}) {
  const { ref, width } = useContainerWidth<HTMLDivElement>(420);
  if (!series.length) {
    return <p className="exec-mini-empty">Série indisponível para o filtro atual.</p>;
  }
  const W = width;
  const H = height;
  const pad = { t: 14, r: 12, b: 22, l: 12 };
  const iw = Math.max(80, W - pad.l - pad.r);
  const ih = H - pad.t - pad.b;
  const max = Math.max(1, ...series.map((s) => s.total));
  const min = Math.min(...series.map((s) => s.total), 0);
  const range = Math.max(max - min, 1);
  const step = series.length > 1 ? iw / (series.length - 1) : 0;
  const path = series
    .map((p, idx) => {
      const x = pad.l + idx * step;
      const y = pad.t + ih - ((p.total - min) / range) * ih;
      return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const last = series[series.length - 1];
  const lastX = pad.l + (series.length - 1) * step;
  const lastY = pad.t + ih - ((last.total - min) / range) * ih;
  const area =
    `${path} L ${lastX.toFixed(1)},${(pad.t + ih).toFixed(1)} L ${pad.l.toFixed(1)},${(pad.t + ih).toFixed(1)} Z`;
  return (
    <div ref={ref} className="exec-spark">
      <svg viewBox={`0 0 ${W} ${H}`} aria-label="Tendência mensal SP">
        <defs>
          <linearGradient id="exec-spark-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--terra)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--terra)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#exec-spark-grad)" />
        <path
          d={path}
          fill="none"
          stroke="var(--terra-deep, var(--terra))"
          strokeWidth={1.6}
        />
        <circle cx={lastX} cy={lastY} r={3} fill="var(--terra-deep, var(--terra))" />
        <text x={lastX - 4} y={lastY - 8} textAnchor="end" className="exec-spark-tip">
          {formatNumber(last.total)}
        </text>
        {series.map((point, idx) => {
          if (idx % Math.max(1, Math.ceil(series.length / 6)) !== 0) return null;
          const x = pad.l + idx * step;
          return (
            <text
              key={point.label + idx}
              x={x}
              y={H - 4}
              textAnchor="middle"
              className="exec-spark-tick"
            >
              {point.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

export const SEVERITY_COLORS = SEVERITY_COLOR;
