import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { CanonicalCauseRanking } from "../../components/bi/CanonicalCauseRanking";
import { ExpandableCategoryTree } from "../../components/bi/ExpandableCategoryTree";
import {
  CategoriasHBars,
  Sparkline,
  VolumeBarsChart,
  fmtMoney,
  fmtN,
  fmtPct,
  type Categoria
} from "../../components/bi/SeverityCharts";
import { DescricoesTable, type DescricaoRow } from "../../components/bi/DescricoesTable";
import { useAggregation } from "../../hooks/useAggregation";
import { useDescricoes } from "../../hooks/useDescricoes";
import {
  buildCauseRanking,
  type CategoriaSubcausaTreeRow,
  type CauseRankingSourceRow
} from "../../lib/analytics";

const SP_OVERRIDE = { regiao: ["SP"] };

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
  "01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun",
  "07": "jul", "08": "ago", "09": "set", "10": "out", "11": "nov", "12": "dez"
};

function labelMonth(iso: string): string {
  const m = iso.slice(5, 7);
  const y = iso.slice(2, 4);
  return (MONTH_PT[m] || m) + "/" + y;
}

export function SeveridadeDemaisRoute() {
  const overview = useAggregation<OverviewRow>("sp_severidade_demais_overview", SP_OVERRIDE);
  const monthly = useAggregation<MonthlyRow>("sp_severidade_demais_mensal", SP_OVERRIDE);
  const cats = useAggregation<Categoria>("sp_severidade_demais_categorias", SP_OVERRIDE);
  const causas = useAggregation<CauseRankingSourceRow>("sp_severidade_demais_causas", SP_OVERRIDE);
  const ranking = useAggregation<RankingRow>("sp_severidade_demais_ranking", SP_OVERRIDE);
  const tree = useAggregation<CategoriaSubcausaTreeRow>("sp_categoria_subcausa_tree_demais", SP_OVERRIDE);
  const descricoes = useDescricoes<DescricaoRow>("demais", 10);

  const [activeCat, setActiveCat] = useState<string | null>(null);
  const [activeCausa, setActiveCausa] = useState<string | null>(null);

  const ov = overview.data?.data?.[0];
  const months = useMemo(
    () => (monthly.data?.data ?? []).map((r) => labelMonth(r.mes_ingresso)),
    [monthly.data]
  );
  const values = useMemo(
    () => (monthly.data?.data ?? []).map((r) => Number(r.qtd_erros || 0)),
    [monthly.data]
  );
  const catsRows = cats.data?.data ?? [];
  const rankRows = ranking.data?.data ?? [];
  const causeRanking = useMemo(
    () => buildCauseRanking(causas.data?.data ?? []).slice(0, 12),
    [causas.data]
  );

  const total = ov?.total ?? 0;
  const proc = ov?.procedentes ?? 0;
  const improc = ov?.improcedentes ?? 0;
  const pctProc = Number(ov?.pct_procedentes ?? 0) * 100;
  const reinc = ov?.reincidentes_clientes ?? 0;
  const valorMed = Number(ov?.valor_medio_fatura ?? 0);
  const categoriasCount = ov?.categorias_count ?? 0;
  const top3 = Number(ov?.top3_share ?? 0) * 100;
  const deltaTri = Number(ov?.delta_trimestre ?? 0) * 100;
  const deltaStr =
    (deltaTri >= 0 ? "↑ " : "↓ ") +
    Math.abs(deltaTri).toFixed(1).replace(".", ",") +
    "% vs. trim. anterior";

  const loading = overview.isLoading || monthly.isLoading || cats.isLoading;

  return (
    <div className="sev-screen sev-screen--demais" data-sev="demais">
      <section className="sev-hero">
        <div className="sev-hero-grid">
          <div>
            <div className="sev-eyebrow">MIS · Severidade Média + Baixa · SP</div>
            <h1 className="sev-hero-title">
              Cauda longa <em>controlada</em>, com aprendizado constante.
            </h1>
            <p className="sev-hero-lede">
              <b>{fmtN(total)}</b> reclamações Média + Baixa em SP nos últimos 12 meses.{" "}
              <b>{fmtN(proc)}</b> procedentes ({fmtPct(pctProc)}) e{" "}
              <b>{fmtN(improc)}</b> improcedentes — contagem real, não proxy. Distribuídas em{" "}
              <b>{categoriasCount} categorias</b>.
            </p>
            <p className="sev-hero-tech">
              Views dedicadas <code>sp_severidade_demais_*</code>. Procedente e Improcedente
              calculados por contagem direta de <code>flag_resolvido_com_refaturamento</code>.
            </p>
            <div className="sev-funnel-cta">
              <Link to="/bi/severidade-alta" className="cta-link">◆ Ir para Alta</Link>
              <Link to="/bi/severidade-critica" className="cta-link">● Ir para Crítica</Link>
              <Link to="/bi/mis" className="cta-link is-ghost">↑ Voltar ao MIS Executivo</Link>
            </div>
          </div>
          <div className="sev-hero-metric">
            <div className="mini">Volume Demais · SP</div>
            <div className="big">{fmtN(total)}</div>
            <div className="delta">{deltaStr}</div>
          </div>
        </div>
      </section>

      <section className="sev-kpis">
        <Kpi
          dominant
          label="Total Demais"
          tag="12m"
          value={fmtN(total)}
          sub={`${deltaStr.replace(" vs. trim. anterior", "")} · SP`}
        />
        <Kpi
          label="Categorias"
          tag="taxonomia"
          value={String(categoriasCount)}
          sub={`top-3 = ${top3.toFixed(1)}% do vol.`}
        />
        <KpiSplit
          label="Procedência"
          tag="proc/improc · contagem real"
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
          tag={valorMed > 0 ? "média procedentes" : "indisponível"}
          value={valorMed > 0 ? fmtMoney(valorMed) : "—"}
          sub={
            valorMed > 0
              ? `total reclamado ~${fmtMoney(valorMed * Math.max(proc, total))}`
              : "indisponível no recorte"
          }
        />
      </section>

      <section className="sev-grid-12">
        <article className="sev-card sev-col-7">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Volume Demais · mês × ano</h2>
              <p className="sev-c-sub">
                Série mensal 12m · view <code>sp_severidade_demais_mensal</code> · pico em{" "}
                {months[values.indexOf(Math.max(...values))] ?? "—"}
              </p>
            </div>
          </header>
          {loading ? (
            <div className="sev-skeleton" style={{ height: 280 }} />
          ) : (
            <VolumeBarsChart months={months} values={values} sevLabel="demais" />
          )}
        </article>
        <article className="sev-card sev-col-5">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Categorias identificadas</h2>
              <p className="sev-c-sub">Clique para cross-filtrar ranking e descrições</p>
            </div>
          </header>
          {loading ? (
            <div className="sev-skeleton" style={{ height: 280 }} />
          ) : (
            <CategoriasHBars
              rows={catsRows}
              activeId={activeCat}
              onToggle={(id) => setActiveCat((c) => (c === id ? null : id))}
            />
          )}
          <div className="sev-insight">
            <b>Insight:</b> As top-3 categorias concentram <b>{top3.toFixed(1)}%</b> do volume
            Média + Baixa em SP.
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
            <h2 className="sev-c-title">Causas canônicas · ranking</h2>
            <p className="sev-c-sub">
              Top causas em Demais (Média + Baixa) com procedência real. Clique para cross-filtrar.
            </p>
          </div>
        </header>
        {causas.isLoading ? (
          <div className="sev-skeleton" style={{ height: 320 }} />
        ) : (
          <CanonicalCauseRanking
            rows={causeRanking}
            activeId={activeCausa}
            onSelect={setActiveCausa}
            emptyHint="Sem causas rotuladas em Demais para o recorte atual."
          />
        )}
      </article>

      <article className="sev-card" style={{ marginTop: 18 }}>
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">Categoria → subcausa · explorador</h2>
            <p className="sev-c-sub">
              Clique numa subcausa para ver um exemplo real do dataset (texto cleaned do silver).
            </p>
          </div>
        </header>
        <ExpandableCategoryTree
          rows={tree.data?.data ?? []}
          loading={tree.isLoading}
          emptyHint="Sem árvore categoria/subcausa para Demais no recorte atual."
        />
      </article>

      <article className="sev-card" style={{ marginTop: 18 }}>
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">10 descrições identificadas pelo assistente</h2>
            <p className="sev-c-sub">
              Top 10 ordens reais Demais classificadas em causa canônica · expanda para ver ação
              sugerida e top-10 instalações reincidentes.
            </p>
          </div>
        </header>
        <DescricoesTable
          rows={descricoes.data?.data ?? []}
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
              Ordenado por reincidência Demais em SP · categoria predominante e causa canônica
              associada
            </p>
          </div>
        </header>
        {ranking.isLoading ? (
          <div className="sev-skeleton" style={{ height: 320 }} />
        ) : (
          <RankingTable rows={rankRows} />
        )}
      </article>
    </div>
  );
}

function Kpi({
  label,
  value,
  tag,
  sub,
  dominant
}: {
  label: string;
  value: string;
  tag?: string;
  sub?: string;
  dominant?: boolean;
}) {
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
  if (!rows.length)
    return <p className="sev-c-sub">Sem reincidências suficientes para compor o ranking.</p>;
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
