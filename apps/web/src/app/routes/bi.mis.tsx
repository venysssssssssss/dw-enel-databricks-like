import { useMemo } from "react";
import { Hero } from "../../components/bi/Hero";
import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars } from "../../components/bi/Charts";
import {
  MiniBarList,
  MonthlySparkline,
  SEVERITY_COLORS,
  SeverityDonut
} from "../../components/bi/ExecutiveCharts";
import { CanonicalCauseRanking } from "../../components/bi/CanonicalCauseRanking";
import { ExpandableCategoryTree } from "../../components/bi/ExpandableCategoryTree";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { FilterChips } from "../../components/shared/FilterChips";
import { StoryBlock } from "../../components/bi/StoryBlock";
import { useAggregation } from "../../hooks/useAggregation";
import { useRegionScope } from "../../components/shared/RegionScope";
import {
  buildCauseRanking,
  buildMonthlyEvaluatedSeries,
  buildSeverityDistribution,
  buildSubjectModelSummary,
  formatCategoria,
  formatCausa,
  formatMoney,
  formatNumber,
  formatPercent,
  pickAssuntoLiderValor,
  SEVERITY_LABEL_PT,
  type AssuntoLiderRow,
  type CategoriaSubcausaTreeRow,
  type CategoryBreakdownRow,
  type CauseRankingSourceRow,
  type ClassifierCoverageRow,
  type MisRegionRow,
  type MisMonthlyRow,
  type Severity,
  type SeverityHeatmapRow,
  type SubjectModelSummary,
  type TopAssuntoRow
} from "../../lib/analytics";

export function MisRoute() {
  const scope = useRegionScope();
  const subjectScopeRegion = scope === "CE" ? "CE" : "SP";

  const mis = useAggregation<MisRegionRow>("mis");
  const severity = useAggregation<SeverityHeatmapRow>("severity_heatmap");
  const causes = useAggregation<CauseRankingSourceRow>("sp_severidade_alta_causas", { regiao: ["SP"] });
  const causesCrit = useAggregation<CauseRankingSourceRow>("sp_severidade_critica_causas", { regiao: ["SP"] });
  const causesDemais = useAggregation<CauseRankingSourceRow>("sp_severidade_demais_causas", { regiao: ["SP"] });
  const tree = useAggregation<CategoriaSubcausaTreeRow>("sp_categoria_subcausa_tree", { regiao: ["SP"] });
  const categories = useAggregation<CategoryBreakdownRow>("category_breakdown");
  const coverage = useAggregation<ClassifierCoverageRow>("classifier_coverage");
  const monthly = useAggregation<MisMonthlyRow>("mis_monthly_mis");
  const assuntoLider = useAggregation<AssuntoLiderRow>("sp_perfil_assunto_lider");
  const topAssuntos = useAggregation<TopAssuntoRow>("top_assuntos");

  const rows = mis.data?.data ?? [];
  const total = rows.reduce((sum, row) => sum + Number(row.volume_total ?? 0), 0);
  const top = [...rows].sort((a, b) => b.volume_total - a.volume_total)[0];
  const avgCobertura =
    rows.length > 0
      ? rows.reduce((s, r) => s + Number(r.cobertura_rotulo ?? 0), 0) / rows.length
      : 0;

  const severityRows = severity.data?.data ?? [];
  const severityBuckets = useMemo(
    () => buildSeverityDistribution(severityRows),
    [severityRows]
  );

  const ranking = useMemo(() => {
    const merged = new Map<string, CauseRankingSourceRow>();
    const push = (row: CauseRankingSourceRow) => {
      const key = String(row.nome ?? row.id ?? "");
      if (!key) return;
      const cur = merged.get(key);
      if (!cur) {
        merged.set(key, { ...row });
        return;
      }
      const curVol = Number(cur.vol ?? 0);
      const newVol = Number(row.vol ?? 0);
      const curProc = Number(cur.proc ?? 0);
      const newProc = Number(row.proc ?? 0);
      const totalVol = curVol + newVol;
      const blendedProc = totalVol > 0 ? (curProc * curVol + newProc * newVol) / totalVol : 0;
      merged.set(key, {
        ...cur,
        vol: totalVol,
        proc: blendedProc,
        reinc: Number(cur.reinc ?? 0) + Number(row.reinc ?? 0),
        cat: cur.cat || row.cat
      });
    };
    for (const r of causes.data?.data ?? []) push(r);
    for (const r of causesCrit.data?.data ?? []) push(r);
    for (const r of causesDemais.data?.data ?? []) push(r);
    return buildCauseRanking(Array.from(merged.values())).slice(0, 10);
  }, [causes.data, causesCrit.data, causesDemais.data]);

  const treeRows = tree.data?.data ?? [];

  const causasIdentificadas = useMemo(
    () => Array.from(new Set(ranking.map((r) => r.id))).filter(Boolean).length,
    [ranking]
  );

  const dominantCausa = top?.causa_dominante ?? "";
  const dominantCausaLabel = dominantCausa ? formatCausa(dominantCausa) : "…";

  const subjectSummary = useMemo(
    () =>
      buildSubjectModelSummary({
        topAssuntos: topAssuntos.data?.data ?? [],
        classifierCoverage: coverage.data?.data ?? [],
        categoryBreakdown: categories.data?.data ?? [],
        severityHeatmap: severityRows,
        misRegions: rows,
        scopeRegiao: subjectScopeRegion
      }),
    [topAssuntos.data, coverage.data, categories.data, severityRows, rows, subjectScopeRegion]
  );

  const monthlySeries = useMemo(
    () =>
      buildMonthlyEvaluatedSeries(monthly.data?.data ?? [], {
        regiao: subjectScopeRegion,
        maxMonths: 12
      }),
    [monthly.data, subjectScopeRegion]
  );

  const valorLider = useMemo(
    () => pickAssuntoLiderValor(assuntoLider.data?.data ?? []),
    [assuntoLider.data]
  );

  const valorKpi = valorLider.hasValue
    ? {
        value: formatMoney(valorLider.valor),
        sub: `Assunto líder SP · ${valorLider.assunto || "—"}`,
        tag: "R$ · SP"
      }
    : {
        value: "—",
        sub: "Indisponível no contrato Web atual",
        tag: "R$"
      };

  return (
    <div className="route-stack">
      <Hero
        eyebrow="BI / MIS Executivo"
        title={
          <>
            Volume → severidade → causa → <em>ação</em>
          </>
        }
        description="Topo de funil executivo. Começa pelo total filtrado, mostra onde está o volume regional, abre a severidade como funil e leva a Alta, Crítica e Demais para aprofundamento."
        metricLabel="Ordens filtradas"
        metricValue={formatNumber(total)}
        metricDelta={top ? `Pico · ${top.regiao}` : ""}
      />
      <FilterChips />
      <KpiStrip
        items={[
          { label: "Volume total", value: formatNumber(total), tag: "filtrado", dominant: true },
          { label: "Região líder", value: top?.regiao ?? "…", tag: "pico" },
          {
            label: "Causa dominante",
            value: dominantCausaLabel,
            tag: "top-1",
            title: dominantCausa
              ? `Causa dominante: ${dominantCausaLabel} (id: ${dominantCausa})`
              : undefined
          },
          {
            label: "Causas identificadas",
            value: formatNumber(causasIdentificadas),
            tag: "ranking SP",
            sub: "via classificador v3"
          },
          { label: "Cobertura rótulo", value: formatPercent(avgCobertura * 100), tag: "ml" },
          { label: "Valor médio fatura", value: valorKpi.value, sub: valorKpi.sub, tag: valorKpi.tag }
        ]}
      />
      <StoryBlock lead="Onde está o volume e onde ele pesa?">
        Regiões com maior <b>volume absoluto</b> não são sempre as mais críticas. Cruze com{" "}
        <b>severidade</b>, <b>cobertura do modelo</b> e <b>procedência exata</b> antes de priorizar
        revisão.
      </StoryBlock>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">Volume por região</h2>
            <p className="card-sub">Base atual do dataset versionado.</p>
          </div>
        </div>
        <VolumeBars data={rows} xKey="regiao" yKey="volume_total" />
      </section>
      <section className="exec-pair-grid">
        <article className="card exec-card">
          <header className="card-head">
            <div>
              <h2 className="card-title">Distribuição por severidade</h2>
              <p className="card-sub">
                Funil derivado da taxonomia oficial. Soma <b>qtd_erros</b> por severidade no
                recorte atual.
              </p>
            </div>
          </header>
          {severity.isLoading ? (
            <div className="exec-empty exec-loading">Carregando…</div>
          ) : (
            <SeverityDonut buckets={severityBuckets} height={300} />
          )}
        </article>
        <article className="card exec-card">
          <header className="card-head">
            <div>
              <h2 className="card-title">Causas canônicas · ranking</h2>
              <p className="card-sub">
                Top causas em SP combinando Alta + Crítica + Demais. Procedente/Improcedente
                derivados de contagem real (vol × % procedência) — sem proxy.
              </p>
            </div>
          </header>
          {causes.isLoading || causesCrit.isLoading || causesDemais.isLoading ? (
            <div className="exec-empty exec-loading">Carregando…</div>
          ) : (
            <CanonicalCauseRanking
              rows={ranking}
              emptyHint="Sem causas rotuladas suficientes — ajuste o filtro ou aguarde nova carga."
            />
          )}
        </article>
      </section>
      <section className="card exec-card">
        <header className="card-head">
          <div>
            <h2 className="card-title">Categoria → subcausa · explorador</h2>
            <p className="card-sub">
              Clique numa categoria para abrir as subcausas; clique numa subcausa para ler um{" "}
              <b>exemplo real do dataset</b>. Procedente/Improcedente são contagens reais por
              subcausa. Nada é inventado.
            </p>
          </div>
        </header>
        <ExpandableCategoryTree
          rows={treeRows}
          loading={tree.isLoading}
          emptyHint="View sp_categoria_subcausa_tree sem dados para o recorte atual."
        />
      </section>
      <SubjectCoverageCard
        summary={subjectSummary}
        monthlySeries={monthlySeries}
        scopeRegion={subjectScopeRegion}
        scope={scope}
        loading={
          topAssuntos.isLoading ||
          coverage.isLoading ||
          categories.isLoading ||
          severity.isLoading
        }
      />
      <section className="table-section">
        <h2 className="card-title" style={{ marginBottom: 12 }}>
          Resumo regional
        </h2>
        <table>
          <thead>
            <tr>
              <th>Região</th>
              <th>Ordens</th>
              <th>Cobertura</th>
              <th>Crítico</th>
              <th>Causa dominante</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.regiao}>
                <td>
                  <b>{row.regiao}</b>
                </td>
                <td>{formatNumber(row.volume_total)}</td>
                <td>{formatPercent(Number(row.cobertura_rotulo ?? 0) * 100)}</td>
                <td>{formatPercent(Number(row.share_critico ?? 0) * 100)}</td>
                <td title={row.causa_dominante}>{formatCausa(row.causa_dominante)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <AssistantCta area="MIS Executivo" />
    </div>
  );
}

function SubjectCoverageCard({
  summary,
  monthlySeries,
  scopeRegion,
  scope,
  loading
}: {
  summary: SubjectModelSummary;
  monthlySeries: { label: string; total: number; iso: string }[];
  scopeRegion: "SP" | "CE";
  scope: "ALL" | "SP" | "CE";
  loading: boolean;
}) {
  const subjectScopeNote = summary.subjectFromFilter
    ? "Filtro de assunto ativo"
    : "Assunto dominante no filtro atual";
  const evaluatedNote =
    summary.evaluatedConfidenceNote === "high_low"
      ? "buckets high + low"
      : "apenas alta confiança";
  const categoryRows = summary.categoryDistribution.slice(0, 6).map((row, idx) => ({
    label: formatCategoria(row.categoria),
    value: row.value,
    pct: row.pct,
    color: PALETTE[idx % PALETTE.length]
  }));
  const severityRows = summary.severityDistribution
    .filter((bucket) => bucket.value > 0)
    .map((bucket) => ({
      label: SEVERITY_LABEL_PT[bucket.key as Severity],
      value: bucket.value,
      pct: bucket.pct,
      color: SEVERITY_COLORS[bucket.key as Severity]
    }));
  return (
    <section className="card exec-subject-card">
      <header className="card-head">
        <div>
          <h2 className="card-title">Cobertura do assunto e do modelo · {scopeRegion}</h2>
          <p className="card-sub">
            {subjectScopeNote}. Avaliados pelo modelo = <code>{evaluatedNote}</code>.{" "}
            {summary.hasSubjectScopedEvaluation
              ? null
              : `Cobertura por assunto exige view agregada dedicada — exibido proxy global ${scopeRegion}.`}{" "}
            {scope === "ALL"
              ? "Filtro regional do topo está em Todas — narrativa primária permanece em SP."
              : null}
          </p>
        </div>
      </header>
      {loading ? (
        <div className="exec-empty exec-loading">Carregando agregações…</div>
      ) : (
        <div className="exec-subject-grid">
          <div className="exec-subject-kpis">
            <SubjectKpi
              label={`Total reclamações ${scopeRegion}`}
              value={formatNumber(summary.totalSp)}
              tag="12m"
              dominant
            />
            <SubjectKpi
              label={`Total · ${summary.subjectName || "—"}`}
              value={formatNumber(summary.subjectTotal)}
              tag="assunto líder"
            />
            <SubjectKpi
              label="% do assunto sobre o todo"
              value={formatPercent(summary.subjectShare)}
              tag="share"
            />
            <SubjectKpi
              label={`Avaliados pelo modelo · ${scopeRegion}`}
              value={formatNumber(summary.evaluatedSp)}
              tag="confiança ≠ indefinido"
            />
            <SubjectKpi
              label={`% modelo sobre ${scopeRegion}`}
              value={formatPercent(summary.evaluatedShareSp)}
              tag="cobertura"
            />
            <SubjectKpi
              label="Categorias encontradas"
              value={formatNumber(summary.categoriesFound)}
              tag="taxonomia"
            />
          </div>
          <div className="exec-subject-spark">
            <div className="spark-head">
              <h3>Avaliados · tendência mensal {scopeRegion}</h3>
              <span>
                {monthlySeries.length} meses · proxy do total {scopeRegion} no contrato Web
              </span>
            </div>
            <MonthlySparkline series={monthlySeries} height={120} />
          </div>
          <div className="exec-subject-bars">
            <div className="bars-head">
              <h3>Distribuição por categoria · {scopeRegion}</h3>
              <span>Top 6 categorias</span>
            </div>
            <MiniBarList
              rows={categoryRows}
              emptyHint={`Sem categorias rotuladas para ${scopeRegion}.`}
            />
          </div>
          <div className="exec-subject-bars">
            <div className="bars-head">
              <h3>Distribuição por severidade · {scopeRegion}</h3>
              <span>Funil completo</span>
            </div>
            <MiniBarList rows={severityRows} emptyHint="Sem severidade no recorte." />
          </div>
        </div>
      )}
    </section>
  );
}

function SubjectKpi({
  label,
  value,
  tag,
  dominant
}: {
  label: string;
  value: string;
  tag?: string;
  dominant?: boolean;
}) {
  return (
    <article className={"exec-subject-kpi" + (dominant ? " is-dominant" : "")}>
      <div className="head">
        <span className="lbl">{label}</span>
        {tag ? <span className="tag">{tag}</span> : null}
      </div>
      <div className="val">{value}</div>
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
