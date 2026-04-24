import { useQuery } from "@tanstack/react-query";
import { fetchAggregation } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import { useDatasetVersion } from "./useDatasetVersion";
import { useFiltersStore, filtersToApiContract } from "../state/filters-store";

export function useAggregation<T>(
  viewId: string,
  overrides: Record<string, unknown> = {}
) {
  const version = useDatasetVersion();
  const datasetHash = version.data?.hash ?? "pending";
  const filters = useFiltersStore();
  const apiFilters = { ...filtersToApiContract(filters), ...overrides };
  const query = useQuery({
    queryKey: queryKeys.aggregation(viewId, apiFilters, datasetHash),
    queryFn: () => fetchAggregation<T>(viewId, apiFilters, datasetHash),
    enabled: Boolean(version.data?.hash),
    staleTime: 60_000
  });
  return { ...query, datasetHash, version: version.data };
}
