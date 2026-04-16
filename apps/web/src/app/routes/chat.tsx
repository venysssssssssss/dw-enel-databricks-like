import { ChatPanel } from "../../components/chat/ChatPanel";
import { KpiStrip } from "../../components/bi/KpiStrip";
import { useAggregation } from "../../hooks/useAggregation";

type Overview = {
  total_registros: number;
  regioes: number;
  topicos: number;
  taxa_refaturamento: number;
};

export function ChatRoute() {
  const overview = useAggregation<Overview>("overview");
  const row = overview.data?.data[0];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>Assistente ENEL</p>
        <h1>Chat conectado ao mesmo dataset do BI</h1>
      </section>
      <KpiStrip
        items={[
          { label: "Ordens", value: row?.total_registros ?? "..." },
          { label: "Regiões", value: row?.regioes ?? "..." },
          { label: "Tópicos", value: row?.topicos ?? "..." },
          {
            label: "Refaturamento",
            value: row ? `${(row.taxa_refaturamento * 100).toFixed(1)}%` : "..."
          }
        ]}
      />
      <ChatPanel datasetHash={overview.datasetHash} />
    </div>
  );
}
