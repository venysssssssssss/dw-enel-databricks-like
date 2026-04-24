import { useSearch } from "@tanstack/react-router";
import { ChatPanel } from "../../components/chat/ChatPanel";
import { useAggregation } from "../../hooks/useAggregation";

type Overview = {
  total_registros: number;
  regioes: number;
  topicos: number;
  taxa_refaturamento: number;
};

export function ChatRoute() {
  const overview = useAggregation<Overview>("overview");
  const search = useSearch({ strict: false }) as { context?: string };
  const contextHint = search?.context;

  return <ChatPanel datasetHash={overview.datasetHash} contextHint={contextHint} />;
}
