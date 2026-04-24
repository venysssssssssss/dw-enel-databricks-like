import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars } from "../../components/bi/Charts";
import { PageHeading } from "../../components/shared/PageHeading";
import { FilterChips } from "../../components/shared/FilterChips";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { StoryBlock } from "../../components/bi/StoryBlock";
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
  const causeRows = causes.data?.data ?? [];
  const topCause = [...causeRows].sort((a, b) => b.taxa_refaturamento - a.taxa_refaturamento)[0];

  return (
    <div className="route-stack">
      <PageHeading
        eyebrow="BI / Impacto"
        title="Refaturamento como desfecho operacional"
        emphasis="desfecho"
      />
      <FilterChips />
      <KpiStrip
        items={[
          {
            label: "Ordens",
            value: row ? formatNumber(row.total) : "…",
            tag: "universo",
            dominant: true
          },
          { label: "Refaturadas", value: row ? formatNumber(row.refaturadas) : "…", tag: "desfecho" },
          {
            label: "Taxa",
            value: row ? `${(row.taxa_refaturamento * 100).toFixed(1)}%` : "…",
            tag: "global"
          },
          {
            label: "Causa crítica",
            value: topCause?.causa_canonica ?? "…",
            tag: topCause ? `${(topCause.taxa_refaturamento * 100).toFixed(1)}%` : ""
          }
        ]}
      />
      <StoryBlock lead="Onde o retrabalho sangra mais?">
        Refaturamento é o sinal terminal de erro. Causas com <b>alta taxa</b> mas volume baixo são
        candidatas a <b>auditoria focada</b>; causas com volume alto e taxa média pedem{" "}
        <b>ajuste de processo</b>.
      </StoryBlock>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">Causas com maior taxa</h2>
            <p className="card-sub">Ranking por taxa e volume.</p>
          </div>
        </div>
        <VolumeBars data={causeRows} xKey="causa_canonica" yKey="qtd_erros" />
      </section>
      <AssistantCta area="Impacto" />
    </div>
  );
}

function formatNumber(n: number | string): string {
  return Number(n).toLocaleString("pt-BR");
}
