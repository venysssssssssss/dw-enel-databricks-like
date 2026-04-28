import { useQuery } from "@tanstack/react-query";
import { fetchDescricoes, type DescricoesResponse, type DescricoesLevel } from "../lib/api";
import { useDatasetVersion } from "./useDatasetVersion";
import { useFiltersStore } from "../state/filters-store";

export function useDescricoes<T>(level: DescricoesLevel, limit = 10) {
  const version = useDatasetVersion();
  const datasetHash = version.data?.hash ?? "pending";
  const start = useFiltersStore((s) => s.start);
  const end = useFiltersStore((s) => s.end);
  const query = useQuery<DescricoesResponse<T>>({
    queryKey: ["descricoes", level, limit, datasetHash, start ?? "-", end ?? "-"],
    queryFn: () => fetchDescricoes<T>(level, datasetHash, limit, { start, end }),
    enabled: Boolean(version.data?.hash),
    staleTime: 30_000
  });
  return { ...query, datasetHash };
}
