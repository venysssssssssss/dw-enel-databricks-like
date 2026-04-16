import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

type IslandProps = {
  theme: "light" | "dark";
  datasetHash: string;
  totalFiltered: number;
  totalAvailable: number;
  refaturamentoRate: number;
  labelRate: number;
  regions: string[];
  topCause: string;
};

const formatInt = (value: number) => new Intl.NumberFormat("pt-BR").format(value);
const formatPct = (value: number) =>
  new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(value);

function OperationalIsland(props: IslandProps) {
  const [expanded, setExpanded] = useState(false);
  const coverage = props.totalAvailable > 0 ? props.totalFiltered / props.totalAvailable : 0;
  const riskState = useMemo(() => {
    if (props.refaturamentoRate >= 0.2) return "Atenção";
    if (props.refaturamentoRate >= 0.08) return "Monitorar";
    return "Normal";
  }, [props.refaturamentoRate]);

  return (
    <section className={`ts-island ts-island--${props.theme}`} aria-label="Painel TypeScript">
      <div className="ts-island__header">
        <div>
          <span className="ts-island__eyebrow">TypeScript aplicado no Streamlit</span>
          <h2>Pulso operacional</h2>
        </div>
        <button type="button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Resumo" : "Detalhar"}
        </button>
      </div>
      <div className="ts-island__grid">
        <Metric label="Escopo filtrado" value={formatInt(props.totalFiltered)} detail={formatPct(coverage)} />
        <Metric label="Refaturamento" value={formatPct(props.refaturamentoRate)} detail={riskState} />
        <Metric label="Causa dominante" value={props.topCause || "n/d"} detail={`${props.regions.length} regiões`} />
      </div>
      <div className="ts-island__bar" aria-label={`Cobertura ${formatPct(coverage)}`}>
        <span style={{ width: `${Math.max(2, Math.min(100, coverage * 100))}%` }} />
      </div>
      {expanded ? (
        <div className="ts-island__details">
          <code>{props.datasetHash.slice(0, 16)}</code>
          <span>Cobertura de causa-raiz: {formatPct(props.labelRate)}</span>
          <span>Regiões: {props.regions.join(", ") || "n/d"}</span>
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="ts-island__metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

const styles = `
  .ts-island {
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    border: 1px solid var(--island-border);
    border-radius: 18px;
    padding: 18px;
    background: var(--island-surface);
    color: var(--island-text);
    box-shadow: var(--island-shadow);
  }
  .ts-island--light {
    --island-surface: linear-gradient(135deg, #ffffff 0%, #fff7f8 100%);
    --island-text: #1f2329;
    --island-muted: #626b76;
    --island-border: #ead4da;
    --island-shadow: 0 14px 34px rgba(135, 10, 60, 0.10);
  }
  .ts-island--dark {
    --island-surface: linear-gradient(135deg, #191b20 0%, #27121c 100%);
    --island-text: #fbf7f9;
    --island-muted: #d8c3cb;
    --island-border: #6d3149;
    --island-shadow: 0 18px 42px rgba(0, 0, 0, 0.32);
  }
  .ts-island__header {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }
  .ts-island__eyebrow {
    display: block;
    color: var(--island-muted);
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0;
  }
  .ts-island h2 {
    margin: 3px 0 0;
    font-size: 22px;
    line-height: 1.12;
  }
  .ts-island button {
    min-height: 36px;
    border: 1px solid #c8102e;
    border-radius: 8px;
    padding: 0 12px;
    background: #c8102e;
    color: #fff;
    font-weight: 800;
    cursor: pointer;
  }
  .ts-island__grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }
  .ts-island__metric {
    min-width: 0;
    display: grid;
    gap: 6px;
    padding: 12px;
    border: 1px solid var(--island-border);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.06);
  }
  .ts-island__metric span,
  .ts-island__metric small {
    color: var(--island-muted);
    overflow-wrap: anywhere;
  }
  .ts-island__metric span {
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
  }
  .ts-island__metric strong {
    font-size: 23px;
    line-height: 1;
    overflow-wrap: anywhere;
  }
  .ts-island__bar {
    height: 9px;
    margin-top: 14px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(200, 16, 46, 0.16);
  }
  .ts-island__bar span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #870a3c, #c8102e, #e4002b);
    transition: width 280ms ease;
  }
  .ts-island__details {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    color: var(--island-muted);
  }
  .ts-island__details code,
  .ts-island__details span {
    border: 1px solid var(--island-border);
    border-radius: 8px;
    padding: 6px 8px;
  }
  @media (max-width: 700px) {
    .ts-island__grid { grid-template-columns: 1fr; }
    .ts-island__header { flex-direction: column; }
  }
`;

function mount() {
  const host = document.getElementById("enel-streamlit-island");
  const data = document.getElementById("enel-streamlit-island-data");
  if (!host || !data?.textContent) return;
  const props = JSON.parse(data.textContent) as IslandProps;
  const style = document.createElement("style");
  style.textContent = styles;
  document.head.appendChild(style);
  createRoot(host).render(<OperationalIsland {...props} />);
}

mount();
