import { useMemo } from "react";
import { Link } from "@tanstack/react-router";
import {
  MiniBarList,
  MonthlySparkline,
  SEVERITY_COLORS,
  SeverityDonut
} from "../../components/bi/ExecutiveCharts";
import { useAggregation } from "../../hooks/useAggregation";
import {
  buildMonthlyEvaluatedSeries,
  buildProcedenciaSplit,
  buildSeverityDistribution,
  formatMoney,
  formatNumber,
  formatPercent,
  SEVERITY_LABEL_PT,
  weightedFaturaMedia,
  type CategoryBreakdownRow,
  type FaturaMedidorRow,
  type MisMonthlyRow,
  type Severity,
  type SeverityHeatmapRow
} from "../../lib/analytics";

const FOCUS: Severity[] = ["medium", "low"];
// Tela é SP-locked: severidade Alta/Crítica/Demais sempre referem a SP.
const SP_OVERRIDE = { regiao: ["SP"] };

export function SeveridadeDemaisRoute() {
  const severity = useAggregation<SeverityHeatmapRow>("severity_heatmap", SP_OVERRIDE);
  const categories = useAggregation<CategoryBreakdownRow>("category_breakdown", SP_OVERRIDE);
  const monthly = useAggregation<MisMonthlyRow>("mis_monthly_mis", SP_OVERRIDE);
  const fatura = useAggregation<FaturaMedidorRow>("sp_fatura_medidor", SP_OVERRIDE);

  const buckets = useMemo(
    () => buildSeverityDistribution(severity.data?.data ?? [], { regiao: "SP" }),
    [severity.data]
  );
  const focused = buckets.filter((bucket) => FOCUS.includes(bucket.key as Severity));
  const focusTotal = focused.reduce((sum, b) => sum + b.value, 0);
  const allTotal = buckets.reduce((sum, b) => sum + b.value, 0);
  const focusShare = allTotal > 0 ? (focusTotal / allTotal) * 100 : 0;

  const procedencia = useMemo(
    () =>
      buildProcedenciaSplit(severity.data?.data ?? [], {
        regiao: "SP",
        severities: FOCUS
      }),
    [severity.data]
  );

  const fatRows = fatura.data?.data ?? [];
  const fatStats = useMemo(() => weightedFaturaMedia(fatRows), [fatRows]);

  const refatRows = (severity.data?.data ?? []).filter(
    (row) =>
      String(row.regiao ?? "").toUpperCase() === "SP" &&
      FOCUS.includes(String(row.severidade ?? "").toLowerCase() as Severity)
  );
  const weightedRefat = useMemo(() => {
    const totals = refatRows.reduce(
      (acc, row) => {
        const vol = Number(row.qtd_erros ?? 0);
        acc.vol += vol;
        acc.refat += vol * Number(row.taxa_refaturamento ?? 0);
        return acc;
      },
      { vol: 0, refat: 0 }
    );
    return totals.vol > 0 ? (totals.refat / totals.vol) * 100 : 0;
  }, [refatRows]);

  const categoryRows = useMemo(() => {
    const sp = (categories.data?.data ?? []).filter(
      (row) => String(row.regiao ?? "").toUpperCase() === "SP"
    );
    const total = sp.reduce((s, r) => s + Number(r.qtd_erros ?? 0), 0);
    return sp
      .map((row, idx) => ({
        label: String(row.categoria ?? "nao_classificada").replaceAll("_", " "),
        value: Number(row.qtd_erros ?? 0),
        pct: total > 0 ? (Number(row.qtd_erros ?? 0) / total) * 100 : 0,
        color: PALETTE[idx % PALETTE.length]
      }))
      .sort((a, b) => b.value - a.value);
  }, [categories.data]);

  const monthlySeries = useMemo(
    () => buildMonthlyEvaluatedSeries(monthly.data?.data ?? [], { regiao: "SP", maxMonths: 12 }),
    [monthly.data]
  );

  const splitRows = focused.map((bucket) => ({
    label: SEVERITY_LABEL_PT[bucket.key as Severity],
    value: bucket.value,
    pct: bucket.pct,
    color: SEVERITY_COLORS[bucket.key as Severity]
  }));

  const totalReclamadoFocus =
    fatStats.valor > 0 && focusTotal > 0 ? fatStats.valor * focusTotal : 0;

  const loading =
    severity.isLoading || categories.isLoading || monthly.isLoading || fatura.isLoading;

  return (
    <div className="sev-screen sev-screen--demais" data-sev="demais">
      <section className="sev-hero">
        <div className="sev-hero-grid">
          <div>
            <div className="sev-eyebrow">MIS · Severidade Média + Baixa · SP</div>
            <h1 className="sev-hero-title">
              Cauda longa <em>controlada</em>, mas com aprendizado constante.
            </h1>
            <p className="sev-hero-lede">
              <b>{formatNumber(focusTotal)}</b> reclamações em SP nas severidades{" "}
              <b>Média</b> e <b>Baixa</b>. Representam{" "}
              <b>{formatPercent(focusShare)}</b> do volume SP no recorte atual. Refaturamento
              ponderado <b>{formatPercent(weightedRefat)}</b>.
            </p>
            <p className="sev-hero-tech">
              SP-locked. Valor médio de fatura derivado de{" "}
              <code>sp_fatura_medidor</code> (média ponderada por volume de ordens). Ranking
              individual por severidade exige view agregada dedicada.
            </p>
            <div className="sev-funnel-cta">
              <Link to="/bi/severidade-alta" className="cta-link">
                ◆ Ir para Alta
              </Link>
              <Link to="/bi/severidade-critica" className="cta-link">
                ● Ir para Crítica
              </Link>
              <Link to="/bi/mis" className="cta-link is-ghost">
                ↑ Voltar ao MIS Executivo
              </Link>
            </div>
          </div>
          <div className="sev-hero-metric">
            <div className="mini">Volume Demais · SP</div>
            <div className="big">{formatNumber(focusTotal)}</div>
            <div className="delta">{formatPercent(focusShare)} do volume SP</div>
          </div>
        </div>
      </section>

      <section className="sev-kpis">
        {focused.map((bucket) => (
          <article
            key={bucket.key}
            className={
              "sev-kpi" + (bucket.key === "medium" ? " is-dominant" : "")
            }
          >
            <div className="sev-kpi-head">
              <span className="sev-kpi-label">{SEVERITY_LABEL_PT[bucket.key as Severity]}</span>
              <span className="sev-kpi-tag">SP · 12m</span>
            </div>
            <div className="sev-kpi-val">{formatNumber(bucket.value)}</div>
            <div className="sev-kpi-sub">{formatPercent(bucket.pct)} do total SP</div>
          </article>
        ))}
        <ProcSplitKpi data={procedencia} />
        <ValorMedioFaturaKpi
          valor={fatStats.valor}
          totalReclamado={totalReclamadoFocus}
          qtdOrdens={fatStats.qtdOrdens}
          loading={fatura.isLoading}
        />
      </section>

      <section className="sev-grid-12">
        <article className="sev-card sev-col-7">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Severidade Média vs Baixa · SP</h2>
              <p className="sev-c-sub">
                Soma <b>qtd_erros</b> da view <code>severity_heatmap</code>. Média representa o
                segmento operacional cuidadoso; Baixa = ruído estrutural recorrente.
              </p>
            </div>
          </header>
          {loading ? (
            <div className="sev-skeleton" style={{ height: 280 }} />
          ) : (
            <SeverityDonut
              buckets={focused}
              height={280}
              emptyHint="Sem volume Média + Baixa para SP no recorte atual."
            />
          )}
        </article>
        <article className="sev-card sev-col-5">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Quebra rápida</h2>
              <p className="sev-c-sub">Volume comparativo entre severidades não-críticas.</p>
            </div>
          </header>
          <MiniBarList
            rows={splitRows}
            emptyHint="Sem severidades não-críticas no recorte SP."
          />
          <div className="sev-insight">
            <b>Leitura:</b> Demais é a janela onde aprendizado de modelo gera ganho composto —
            volume amortizado por melhor classificação reduz refaturamento e chamados
            subsequentes.
          </div>
        </article>
      </section>

      <section className="sev-grid-12">
        <article className="sev-card sev-col-7">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Tendência mensal SP · proxy</h2>
              <p className="sev-c-sub">
                Série de <b>qtd_erros</b> total SP em <code>mis_monthly_mis</code>. Sem split por
                severidade no contrato atual — útil como contexto, não como métrica direta de
                Média/Baixa.
              </p>
            </div>
          </header>
          {loading ? (
            <div className="sev-skeleton" style={{ height: 140 }} />
          ) : (
            <MonthlySparkline series={monthlySeries} height={140} />
          )}
        </article>
        <article className="sev-card sev-col-5">
          <header className="sev-c-head">
            <div>
              <h2 className="sev-c-title">Categorias · SP (todas severidades)</h2>
              <p className="sev-c-sub">
                Top categorias da taxonomia em SP. Não é possível separar Média/Baixa via{" "}
                <code>category_breakdown</code> — ranking exigiria view dedicada.
              </p>
            </div>
          </header>
          <MiniBarList
            rows={categoryRows.slice(0, 6)}
            emptyHint="Sem categorias rotuladas no recorte."
          />
        </article>
      </section>

      <section className="sev-card">
        <header className="sev-c-head">
          <div>
            <h2 className="sev-c-title">Limitações conhecidas desta tela</h2>
            <p className="sev-c-sub">
              Esta página é honesta sobre o contrato atual: telas Alta e Crítica usam views
              dedicadas (<code>sp_severidade_alta_*</code>, <code>sp_severidade_critica_*</code>);
              Demais reaproveita as views genéricas. Para paridade plena, criar
              <code> sp_severidade_demais_*</code> no backend.
            </p>
          </div>
        </header>
        <ul className="sev-limit-list">
          <li>
            <b>Ranking de instalações reincidentes</b>: indisponível — sem view específica para
            Média/Baixa.
          </li>
          <li>
            <b>Valor médio de fatura por severidade</b>: estimado via{" "}
            <code>sp_fatura_medidor</code> ponderado pelo volume de ordens em SP. Mantemos o
            valor real do contrato, não há split direto Média/Baixa.
          </li>
          <li>
            <b>Causas canônicas detalhadas (dispersão volume × procedência)</b>: indisponível para
            Média/Baixa; consulte <Link to="/bi/severidade-alta">Alta</Link> /{" "}
            <Link to="/bi/severidade-critica">Crítica</Link> para equivalente.
          </li>
        </ul>
      </section>
    </div>
  );
}

function ProcSplitKpi({
  data
}: {
  data: { total: number; procedentes: number; improcedentes: number; pctProcedentes: number };
}) {
  const pctProc = data.pctProcedentes;
  const pctImproc = Math.max(0, 100 - pctProc);
  return (
    <article className="sev-kpi">
      <div className="sev-kpi-head">
        <span className="sev-kpi-label">Procedência</span>
        <span className="sev-kpi-tag">proc/improc</span>
      </div>
      <div className="sev-kpi-split">
        <div className="col proc">
          <div className="tiny">procedentes</div>
          <div className="num">{formatNumber(Math.round(data.procedentes))}</div>
          <div className="pct">{formatPercent(pctProc)}</div>
        </div>
        <div className="col improc">
          <div className="tiny">improcedentes</div>
          <div className="num">{formatNumber(Math.round(data.improcedentes))}</div>
          <div className="pct">{formatPercent(pctImproc)}</div>
        </div>
      </div>
      <div className="sev-kpi-mini-bar">
        <span style={{ width: `${Math.max(0, Math.min(100, pctProc))}%` }} />
      </div>
    </article>
  );
}

function ValorMedioFaturaKpi({
  valor,
  totalReclamado,
  qtdOrdens,
  loading
}: {
  valor: number;
  totalReclamado: number;
  qtdOrdens: number;
  loading: boolean;
}) {
  if (loading) {
    return (
      <article className="sev-kpi">
        <div className="sev-kpi-head">
          <span className="sev-kpi-label">Valor médio fatura</span>
          <span className="sev-kpi-tag">SP</span>
        </div>
        <div className="sev-kpi-val">…</div>
        <div className="sev-kpi-sub">carregando agregação</div>
      </article>
    );
  }
  if (valor <= 0) {
    return (
      <article className="sev-kpi">
        <div className="sev-kpi-head">
          <span className="sev-kpi-label">Valor médio fatura</span>
          <span className="sev-kpi-tag">SP</span>
        </div>
        <div className="sev-kpi-val">—</div>
        <div className="sev-kpi-sub">indisponível para SP no recorte</div>
      </article>
    );
  }
  return (
    <article className="sev-kpi">
      <div className="sev-kpi-head">
        <span className="sev-kpi-label">Valor médio fatura</span>
        <span className="sev-kpi-tag">ponderado · SP</span>
      </div>
      <div className="sev-kpi-val">{formatMoney(valor)}</div>
      <div className="sev-kpi-sub">
        {totalReclamado > 0
          ? `total ~${formatMoney(totalReclamado)} sobre ${formatNumber(qtdOrdens)} ordens`
          : `base ${formatNumber(qtdOrdens)} ordens`}
      </div>
    </article>
  );
}

const PALETTE = [
  "var(--terra)",
  "var(--plum)",
  "var(--amber, oklch(74% 0.15 70))",
  "var(--sage)",
  "var(--ocean, var(--terra-deep))",
  "var(--wine, var(--plum-deep))"
];
