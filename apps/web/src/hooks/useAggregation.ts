import { useQuery } from "@tanstack/react-query";
import { fetchAggregation } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import { useDatasetVersion } from "./useDatasetVersion";

export function useAggregation<T>(viewId: string, filters: Record<string, unknown> = {}) {
  const version = useDatasetVersion();
  const datasetHash = version.data?.hash ?? "pending";
  const query = useQuery({
    queryKey: queryKeys.aggregation(viewId, filters, datasetHash),
    queryFn: () => fetchAggregation<T>(viewId, filters, datasetHash),
    enabled: Boolean(version.data?.hash),
    staleTime: 60_000
  });
  return { ...query, datasetHash, version: version.data };
}
