import { VolumeBars } from "../../components/bi/Charts";
import { KpiStrip } from "../../components/bi/KpiStrip";
import { PageHeading } from "../../components/shared/PageHeading";
import { FilterChips } from "../../components/shared/FilterChips";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { StoryBlock } from "../../components/bi/StoryBlock";
import { useAggregation } from "../../hooks/useAggregation";

type TopicRow = {
  topic_name: string;
  qtd_erros: number;
  taxa_refaturamento: number;
};

export function PatternsRoute() {
  const topics = useAggregation<TopicRow>("topic_distribution");
  const rows = topics.data?.data ?? [];
  const total = rows.reduce((s, r) => s + Number(r.qtd_erros ?? 0), 0);
  const top = [...rows].sort((a, b) => b.qtd_erros - a.qtd_erros)[0];
  const avgRefat =
    rows.length > 0
      ? rows.reduce((s, r) => s + Number(r.taxa_refaturamento ?? 0), 0) / rows.length
      : 0;

  return (
    <div className="route-stack">
      <PageHeading
        eyebrow="BI / Padrões"
        title="Tópicos descobertos e concentração operacional"
        emphasis="concentração"
      />
      <FilterChips />
      <KpiStrip
        items={[
          { label: "Tópicos", value: rows.length, tag: "descobertos", dominant: true },
          { label: "Volume", value: formatNumber(total), tag: "somatório" },
          { label: "Tópico líder", value: top?.topic_name ?? "…", tag: "pico" },
          { label: "Refat. média", value: `${(avgRefat * 100).toFixed(1)}%`, tag: "tópicos" }
        ]}
      />
      <StoryBlock lead="Quais narrativas emergem do texto livre?">
        Tópicos descobertos por modelo agrupam causas semanticamente próximas. Use como{" "}
        <b>lente complementar</b> à taxonomia canônica — revelam padrões não codificados.
      </StoryBlock>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">Tópicos descobertos</h2>
            <p className="card-sub">Distribuição calculada no data plane.</p>
          </div>
        </div>
        <VolumeBars data={rows} xKey="topic_name" yKey="qtd_erros" />
      </section>
      <AssistantCta area="Padrões" />
    </div>
  );
}

function formatNumber(n: number | string): string {
  return Number(n).toLocaleString("pt-BR");
}
