import { Hero } from "../../components/bi/Hero";
import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars } from "../../components/bi/Charts";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { FilterChips } from "../../components/shared/FilterChips";
import { StoryBlock } from "../../components/bi/StoryBlock";
import { useAggregation } from "../../hooks/useAggregation";

type MisRow = {
  regiao: string;
  volume_total: number;
  taxa_refaturamento: number;
  cobertura_rotulo: number;
  causa_dominante: string;
  share_critico: number;
};

export function MisRoute() {
  const mis = useAggregation<MisRow>("mis");
  const rows = mis.data?.data ?? [];
  const total = rows.reduce((sum, row) => sum + Number(row.volume_total ?? 0), 0);
  const top = [...rows].sort((a, b) => b.volume_total - a.volume_total)[0];
  const avgRefat =
    rows.length > 0
      ? rows.reduce((s, r) => s + Number(r.taxa_refaturamento ?? 0), 0) / rows.length
      : 0;
  const avgCobertura =
    rows.length > 0
      ? rows.reduce((s, r) => s + Number(r.cobertura_rotulo ?? 0), 0) / rows.length
      : 0;

  return (
    <div className="route-stack">
      <Hero
        eyebrow="BI / MIS Executivo"
        title={
          <>
            Volume, cobertura e <em>severidade</em> por região
          </>
        }
        description="Visão executiva das ordens de erro de leitura. Identifica região dominante, causa líder e cobertura de rotulagem para guiar priorização operacional."
        metricLabel="Ordens filtradas"
        metricValue={formatNumber(total)}
        metricDelta={top ? `Pico: ${top.regiao}` : ""}
      />
      <FilterChips />
      <KpiStrip
        items={[
          { label: "Volume total", value: formatNumber(total), tag: "filtrado", dominant: true },
          { label: "Região líder", value: top?.regiao ?? "…", tag: "pico" },
          { label: "Causa dominante", value: top?.causa_dominante ?? "…", tag: "top-1" },
          { label: "Taxa refaturamento", value: `${(avgRefat * 100).toFixed(1)}%`, tag: "média" },
          { label: "Cobertura rótulo", value: `${(avgCobertura * 100).toFixed(1)}%`, tag: "ml" }
        ]}
      />
      <StoryBlock lead="Onde está o volume e onde ele pesa?">
        Regiões com maior <b>volume absoluto</b> não são sempre as mais críticas. Cruze com{" "}
        <b>taxa de refaturamento</b> e <b>share crítico</b> para priorizar revisão.
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
      <section className="table-section">
        <h2 className="card-title" style={{ marginBottom: 12 }}>
          Resumo regional
        </h2>
        <table>
          <thead>
            <tr>
              <th>Região</th>
              <th>Ordens</th>
              <th>Refat.</th>
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
                <td>{(row.taxa_refaturamento * 100).toFixed(1)}%</td>
                <td>{(row.cobertura_rotulo * 100).toFixed(1)}%</td>
                <td>{(row.share_critico * 100).toFixed(1)}%</td>
                <td>{row.causa_dominante}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <AssistantCta area="MIS Executivo" />
    </div>
  );
}

function formatNumber(n: number | string): string {
  return Number(n).toLocaleString("pt-BR");
}
