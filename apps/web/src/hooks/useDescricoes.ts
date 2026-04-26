import { useQuery } from "@tanstack/react-query";
import { fetchDescricoes, type DescricoesResponse } from "../lib/api";
import { useDatasetVersion } from "./useDatasetVersion";

export function useDescricoes<T>(level: "alta" | "critica", limit = 10) {
  const version = useDatasetVersion();
  const datasetHash = version.data?.hash ?? "pending";
  const query = useQuery<DescricoesResponse<T>>({
    queryKey: ["descricoes", level, limit, datasetHash],
    queryFn: () => fetchDescricoes<T>(level, datasetHash, limit),
    enabled: Boolean(version.data?.hash),
    staleTime: 30_000
  });
  return { ...query, datasetHash };
}
