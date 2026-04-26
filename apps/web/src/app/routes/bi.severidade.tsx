import { useMemo, useState } from "react";
import { useAggregation } from "../../hooks/useAggregation";
import {
  CategoriasHBars,
  CausasScatter,
  Sparkline,
  VolumeBarsChart,
  fmtMoney,
  fmtN,
  fmtPct,
  type Categoria,
  type Causa
} from "../../components/bi/SeverityCharts";
import { DescricoesTable, type DescricaoRow } from "../../components/bi/DescricoesTable";

type Severity = "alta" | "critica";

type OverviewRow = {
  total: number;
  procedentes: number;
  improcedentes: number;
  pct_procedentes: number;
  reincidentes_clientes: number;
  valor_medio_fatura: number;
  categorias_count: number;
  top3_share: number;
  delta_trimestre: number;
};

type MonthlyRow = {
  mes_ingresso: string;
  qtd_erros: number;
  procedentes: number;
  improcedentes: number;
};

type RankingRow = {
  inst: string;
  cat: string;
  causa: string;
  reinc: number;
  valor: number;
  spark: number[];
  cidade: string;
};

const MONTH_PT: Record<string, string> = {
  "01": "jan",
  "02": "fev",
  "03": "mar",
  "04": "abr",
  "05": "mai",
  "06": "jun",
  "07": "jul",
  "08": "ago",
  "09": "set",
  "10": "out",
  "11": "nov",
  "12": "dez"
};

function labelMonth(iso: string): string {
  // "2025-07-01" or "2025-07"
  const m = iso.slice(5, 7);
  const y = iso.slice(2, 4);
  return (MONTH_PT[m] || m) + "/" + y;
}

export function SeveridadeAltaRoute() {
  return <SeveridadeScreen severity="alta" />;
}

export function SeveridadeCriticaRoute() {
  return <SeveridadeScreen severity="critica" />;
}

function SeveridadeScreen({ severity }: { severity: Severity }) {
  const label = severity === "alta" ? "Alta" : "Crítica";
  const viewSuffix = severity === "alta" ? "alta" : "critica";

  const overview = useAggregation<OverviewRow>(`sp_severidade_${viewSuffix}_overview`);
  const monthly = useAggregation<MonthlyRow>(`sp_severidade_${viewSuffix}_mensal`);
  const cats = useAggregation<Categoria>(`sp_severidade_${viewSuffix}_categorias`);
  const causas = useAggregation<Causa>(`sp_severidade_${viewSuffix}_causas`);
  const ranking = useAggregation<RankingRow>(`sp_severidade_${viewSuffix}_ranking`);
  const descricoes = useAggregation<DescricaoRow>(`sp_severidade_${viewSuffix}_descricoes`);

  const [activeCat, setActiveCat] = useState<string | null>(null);
  const [activeCausa, setActiveCausa] = useState<string | null>(null);

  const ov = overview.data?.data?.[0];
  const months = useMemo(() => (monthly.data?.data ?? []).map((r) => labelMonth(r.mes_ingresso)), [monthly.data]);
  const values = useMemo(() => (monthly.data?.data ?? []).map((r) => Number(r.qtd_erros || 0)), [monthly.data]);
  const catsRows = cats.data?.data ?? [];
  const causasRows = causas.data?.data ?? [];
  const rankRows = ranking.data?.data ?? [];

  const total = ov?.total ?? 0;
  const proc = ov?.procedentes ?? 0;
  const improc = ov?.improcedentes ?? 0;
  const pctProc = Number(ov?.pct_procedentes ?? 0) * 100;
  const reinc = ov?.reincidentes_clientes ?? 0;
  const valorMed = ov?.valor_medio_fatura ?? 0;
  const categoriasCount = ov?.categorias_count ?? 0;
  const top3 = Number(ov?.top3_share ?? 0) * 100;
  const deltaTri = Number(ov?.delta_trimestre ?? 0) * 100;
  const deltaStr = (deltaTri >= 0 ? "↑ " : "↓ ") + Math.abs(deltaTri).toFixed(1).replace(".", ",") + "% vs. trim. anterior";

  const loading = overview.isLoading || monthly.isLoading || cats.isLoading;

  return (
    <div className="sev-screen" data-sev={severity}>
      <section className="sev-hero">
        <div className="sev-hero-grid">
          <div>
            <div className="sev-eyebrow">MIS · Severidade {label} · SP</div>
            <h1 className="sev-hero-title">
              {severity === "alta" ? (
                <>
                  Pressão operacional <em>contida</em>, mas em <em>aceleração</em>.
                </>
              ) : (
                <>
                  Baixo volume, <em>alto impacto financeiro</em>.
                </>
              )}
            </h1>
            <p className="sev-hero-lede">
              {severity === "alta" ? (
                <>
                  <b>{fmtN(total)}</b> reclamações <b>alta</b> em SP nos últimos 12 meses, distribuídas em{" "}
                  <b>{categoriasCount} categorias</b>. Valor médio de fatura reclamada{" "}
                  <b>{fmtMoney(valorMed)}</b>. Top-3 concentra <b>{top3.toFixed(1)}%</b> do volume.
                </>
              ) : (
                <>
                  <b>{fmtN(total)}</b> ocorrências <b>críticas</b> em SP. Valor médio da fatura reclamada{" "}
                  <b>{fmtMoney(valorMed)}</b>. Exige resposta operacional coordenada — concentração em poucas
                  categorias ({categoriasCount}).
                </>
              )}
            </p>
            {severity === "critica" && total > 0 ? (
              <div className="sev-urgency">
                <span className="tick">ATENÇÃO</span>
                <span>
                  Crítica responde por apenas {((total / Math.max(total, 1)) * 100).toFixed(1)}% do volume de SP, mas
                  concentra <b>{fmtMoney(valorMed * Math.max(proc, total))}</b> em valor reclamado. Priorização
                  imediata.
                </span>
              </div>
            ) : null}
          </div>
          <div className="sev-hero-metric">
            <div className="mini">Total de reclamações · {label}</div>
            <div className="big">{fmtN(total)}</div>
            <div className="delta">{deltaStr}</div>
          </div>
        </div>
      </section>

      <section className="sev-kpis">
        <Kpi dominant label={`Total ${label}`} tag="12m" value={fmtN(total)} sub={`${deltaStr.replace(" vs. trim. anterior", "")} · SP`} />
        <Kpi
          label="Categorias"
          tag="taxonomia"
          value={String(categoriasCount)}
          sub={`top-3 = ${top3.toFixed(1)}% do vol.`}
        />
        <KpiSplit
          label="Procedência"
          tag="proc/improc"
          proc={proc}
          improc={improc}
          pctProc={pctProc}
        />
        <Kpi
          label="Clientes reincidentes"
          tag="≥ 2 ord."
          value={fmtN(reinc)}
          sub={`${fmtPct((reinc / Math.max(total, 1)) * 100)} · ver ranking abaixo`}
        />
        <Kpi
          label="Valor médio fatura"
          tag="procedentes"
          value={fmtMoney(valorMed)}
          sub={`total reclamado ${fmtMoney(valorMed * Math.max(proc || total, 1))}`}
        />
      </section>

      <section className="sev-story">
        <div className="story-icon">{severity === "alta" ? "◆" : "●"}</div>
        <div className="story-body">
          <span className="lead">
            {severity === "alta" ? "O que a severidade alta diz ao operacional?" : "Por que a severidade crítica muda a prioridade?"}
          </span>
          {severity === "alta"
            ? "Concentração em poucas categorias. Quadrante 'alto volume × alta procedência' sinaliza ajuste de processo, não auditoria individual. Acompanhe sazonalidade mensal."
            : "Apesar do volume menor, cada caso tem valor médio muito acima da média geral e risco reputacional elevado."}
          <div className="story-steps">
            <div className="story-step">
              <span className="n">1</span>Analise a sazonalidade mensal
            </div>
            <div className="story-step">
              <span className="n">2</span>Confronte categoria × causa canônica
            </div>
            <div className="story-step">
              <span className="n">3</span>Priorize instalações do ranking
            </div>
          </div>
        </div>
      </section>

      <section className="sev-grid-12">
        <article className="sev-card sev-col-7">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Volume de reclamações · {label} · mês × ano</h2>
              <p className="sev-c-sub">
                Série mensal 12m · dados reais SP · hover para detalhes · pico em{" "}
                {months[values.indexOf(Math.max(...values))] ?? "—"}
              </p>
            </div>
          </header>
          {loading ? <Skeleton h={280} /> : <VolumeBarsChart months={months} values={values} sevLabel={label.toLowerCase()} />}
        </article>

        <article className="sev-card sev-col-5">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Categorias identificadas</h2>
              <p className="sev-c-sub">Clique para cross-filtrar ranking e causas</p>
            </div>
          </header>
          {loading ? (
            <Skeleton h={280} />
          ) : (
            <CategoriasHBars
              rows={catsRows}
              activeId={activeCat}
              onToggle={(id) => setActiveCat((c) => (c === id ? null : id))}
            />
          )}
          <div className="sev-insight">
            <b>Insight:</b> As top-3 categorias concentram{" "}
            <b>{top3.toFixed(1)}%</b> do volume {label.toLowerCase()} em SP.
            {activeCat ? (
              <a
                href="#"
                className="sev-clear"
                onClick={(e) => {
                  e.preventDefault();
                  setActiveCat(null);
                }}
              >
                limpar filtro
              </a>
            ) : null}
          </div>
        </article>
      </section>

      <article className="sev-card">
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">Causas canônicas · dispersão</h2>
            <p className="sev-c-sub">
              X: volume de ordens · Y: % de procedência · tamanho: reincidências · cor: categoria técnica · clique para
              filtrar
            </p>
          </div>
        </header>
        {causas.isLoading ? (
          <Skeleton h={320} />
        ) : (
          <CausasScatter
            rows={causasRows}
            activeId={activeCausa}
            onToggle={(id) => setActiveCausa((c) => (c === id ? null : id))}
          />
        )}
      </article>

      <article className="sev-card" style={{ marginTop: 18 }}>
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">10 descrições identificadas pelo assistente</h2>
            <p className="sev-c-sub">
              Top 10 ordens reais (texto cleaned do silver) classificadas em causa canônica · expanda para ver
              ação sugerida e top-10 instalações reincidentes na mesma causa
            </p>
          </div>
        </header>
        <DescricoesTable
          rows={(descricoes.data?.data ?? []).slice(0, 10)}
          loading={descricoes.isLoading}
          activeCat={activeCat}
          activeCausa={activeCausa}
        />
      </article>

      <article className="sev-card" style={{ marginTop: 18 }}>
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">Ranking · Top 10 instalações reincidentes</h2>
            <p className="sev-c-sub">
              Ordenado por reincidência {label.toLowerCase()} em SP · categoria predominante e causa canônica
              associada
            </p>
          </div>
        </header>
        {ranking.isLoading ? (
          <Skeleton h={320} />
        ) : (
          <RankingTable rows={rankRows} />
        )}
      </article>
    </div>
  );
}

function Kpi({ label, value, tag, sub, dominant }: { label: string; value: string; tag?: string; sub?: string; dominant?: boolean }) {
  return (
    <article className={"sev-kpi" + (dominant ? " is-dominant" : "")}>
      <div className="sev-kpi-head">
        <span className="sev-kpi-label">{label}</span>
        {tag ? <span className="sev-kpi-tag">{tag}</span> : null}
      </div>
      <div className="sev-kpi-val">{value}</div>
      {sub ? <div className="sev-kpi-sub">{sub}</div> : null}
    </article>
  );
}

function KpiSplit({
  label,
  tag,
  proc,
  improc,
  pctProc
}: {
  label: string;
  tag: string;
  proc: number;
  improc: number;
  pctProc: number;
}) {
  return (
    <article className="sev-kpi">
      <div className="sev-kpi-head">
        <span className="sev-kpi-label">{label}</span>
        <span className="sev-kpi-tag">{tag}</span>
      </div>
      <div className="sev-kpi-split">
        <div className="col proc">
          <div className="tiny">procedentes</div>
          <div className="num">{fmtN(proc)}</div>
          <div className="pct">{fmtPct(pctProc)}</div>
        </div>
        <div className="col improc">
          <div className="tiny">improcedentes</div>
          <div className="num">{fmtN(improc)}</div>
          <div className="pct">{fmtPct(100 - pctProc)}</div>
        </div>
      </div>
      <div className="sev-kpi-mini-bar">
        <span style={{ width: `${Math.max(0, Math.min(100, pctProc))}%` }} />
      </div>
    </article>
  );
}

function RankingTable({ rows }: { rows: RankingRow[] }) {
  if (!rows.length) return <p className="sev-c-sub">Sem reincidências suficientes para compor o ranking.</p>;
  return (
    <table className="sev-rank-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Instalação</th>
          <th>Categoria</th>
          <th>Causa canônica</th>
          <th className="num">Reinc.</th>
          <th className="num">Valor fatura</th>
          <th className="num">Histórico</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.inst + i} className={i < 3 ? "rank-row top-3" : "rank-row"}>
            <td>
              <span className="pos">{i + 1}</span>
            </td>
            <td>
              <span className="inst">{r.inst}</span>
              <div className="sub">{r.cidade}</div>
            </td>
            <td>{r.cat}</td>
            <td className="mono-dim">{r.causa}</td>
            <td className="num">
              <span className="reinc-badge">{r.reinc}×</span>
            </td>
            <td className="num strong">{fmtMoney(r.valor)}</td>
            <td className="num">
              <Sparkline values={r.spark} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Skeleton({ h }: { h: number }) {
  return <div className="sev-skeleton" style={{ height: h }} />;
}
