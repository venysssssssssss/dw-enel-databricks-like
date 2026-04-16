import { VolumeBars } from "../../components/bi/Charts";
import { useAggregation } from "../../hooks/useAggregation";

type TopicRow = {
  topic_name: string;
  qtd_erros: number;
  taxa_refaturamento: number;
};

export function PatternsRoute() {
  const topics = useAggregation<TopicRow>("topic_distribution");
  const rows = topics.data?.data ?? [];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>Padrões</p>
        <h1>Tópicos e concentração operacional</h1>
      </section>
      <section className="chart-section">
        <div>
          <h2>Tópicos descobertos</h2>
          <p>Distribuição calculada no data plane.</p>
        </div>
        <VolumeBars data={rows} xKey="topic_name" yKey="qtd_erros" />
      </section>
    </div>
  );
}
