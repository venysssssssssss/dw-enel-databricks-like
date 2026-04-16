import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars } from "../../components/bi/Charts";
import { useAggregation } from "../../hooks/useAggregation";

type Summary = {
  total: number;
  refaturadas: number;
  taxa_refaturamento: number;
};

type Cause = {
  causa_canonica: string;
  qtd_erros: number;
  taxa_refaturamento: number;
};

export function ImpactRoute() {
  const summary = useAggregation<Summary>("refaturamento_summary");
  const causes = useAggregation<Cause>("refaturamento_by_cause");
  const row = summary.data?.data[0];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>Impacto</p>
        <h1>Refaturamento como desfecho operacional</h1>
      </section>
      <KpiStrip
        items={[
          { label: "Ordens", value: row?.total ?? "..." },
          { label: "Refaturadas", value: row?.refaturadas ?? "..." },
          {
            label: "Taxa",
            value: row ? `${(row.taxa_refaturamento * 100).toFixed(1)}%` : "..."
          }
        ]}
      />
      <section className="chart-section">
        <div>
          <h2>Causas com maior taxa</h2>
          <p>Ranking por taxa e volume.</p>
        </div>
        <VolumeBars data={causes.data?.data ?? []} xKey="causa_canonica" yKey="qtd_erros" />
      </section>
    </div>
  );
}
