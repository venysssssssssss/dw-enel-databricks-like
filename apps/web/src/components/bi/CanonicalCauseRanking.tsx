import { useState } from "react";
import {
  formatCategoria,
  formatNumber,
  formatPercent,
  type CauseRankingRow
} from "../../lib/analytics";

const CAT_TINT: Record<string, string> = {
  operacional: "var(--terra)",
  estimativa: "var(--amber-deep, var(--terra-deep))",
  medidor: "var(--plum)",
  cadastral: "var(--sage)",
  tarifa: "var(--ocean, var(--terra-deep))",
  fraude: "var(--wine, var(--plum))",
  faturamento: "var(--terra-deep)",
  juridico: "var(--plum-deep)",
  contestacao_cliente: "var(--terra)",
  leitura: "var(--terra)",
  consumo: "var(--amber, var(--terra-deep))",
  cadastro: "var(--sage)",
  atendimento: "var(--ocean, var(--plum))",
  tecnico: "var(--plum-deep)",
  nao_classificada: "var(--ink-faint)"
};

function tintFor(cat: string): string {
  return CAT_TINT[cat] || "var(--terra)";
}

export function CanonicalCauseRanking({
  rows,
  emptyHint = "Sem causas suficientes para compor o ranking neste recorte.",
  onSelect,
  activeId,
  topHighlight = 3,
  showCategoria = true
}: {
  rows: CauseRankingRow[];
  emptyHint?: string;
  onSelect?: (id: string | null) => void;
  activeId?: string | null;
  topHighlight?: number;
  showCategoria?: boolean;
}) {
  const [hover, setHover] = useState<string | null>(null);
  if (!rows.length) {
    return <div className="cause-rank cause-rank--empty">{emptyHint}</div>;
  }
  const max = Math.max(1, ...rows.map((r) => r.vol));
  const totalVol = rows.reduce((s, r) => s + r.vol, 0);
  return (
    <ol className="cause-rank" aria-label="Causas canônicas · ranking">
      {rows.map((row, idx) => {
        const isTop = idx < topHighlight;
        const active = activeId === row.id || hover === row.id;
        const wPct = (row.vol / max) * 100;
        const sharePct = totalVol > 0 ? (row.vol / totalVol) * 100 : 0;
        return (
          <li
            key={row.id || row.label + idx}
            className={
              "cause-rank-row" +
              (isTop ? " is-top" : "") +
              (active ? " is-active" : "")
            }
            data-rank={idx + 1}
          >
            <button
              type="button"
              className="cause-rank-btn"
              onClick={() => onSelect?.(activeId === row.id ? null : row.id)}
              onMouseEnter={() => setHover(row.id)}
              onMouseLeave={() => setHover(null)}
              title={`${row.label} · ${formatNumber(row.vol)} ordens`}
            >
              <span className="cause-rank-pos">{idx + 1}</span>
              <div className="cause-rank-body">
                <div className="cause-rank-headline">
                  <span className="cause-rank-label">{row.label}</span>
                  {showCategoria ? (
                    <span
                      className="cause-rank-cat"
                      style={{ borderColor: tintFor(row.categoria) }}
                    >
                      {formatCategoria(row.categoria)}
                    </span>
                  ) : null}
                </div>
                <div className="cause-rank-bar">
                  <span
                    className="cause-rank-bar-fill"
                    style={{
                      width: `${wPct}%`,
                      background: tintFor(row.categoria)
                    }}
                  />
                </div>
                <div className="cause-rank-meta">
                  <span className="cause-rank-meta-vol">
                    <b>{formatNumber(row.vol)}</b> ordens · {formatPercent(sharePct)}
                  </span>
                  <span className="cause-rank-chip is-proc" title="Procedentes (contagem real)">
                    proc <b>{formatNumber(row.proc)}</b>
                  </span>
                  <span className="cause-rank-chip is-improc" title="Improcedentes (contagem real)">
                    improc <b>{formatNumber(row.improc)}</b>
                  </span>
                  <span className="cause-rank-chip is-reinc" title="Instalações reincidentes">
                    reinc <b>{formatNumber(row.reinc)}</b>
                  </span>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
