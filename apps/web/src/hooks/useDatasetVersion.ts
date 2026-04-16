import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { fetchDatasetVersion } from "../lib/api";
import { queryKeys } from "../lib/query-keys";

export function useDatasetVersion() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.dataset,
    queryFn: fetchDatasetVersion,
    staleTime: 0,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true
  });

  useEffect(() => {
    if (query.data?.hash) {
      queryClient.invalidateQueries({
        predicate: (item) => item.queryKey[0] === "aggregation" && item.queryKey[3] !== query.data.hash
      });
    }
  }, [query.data?.hash, queryClient]);

  return query;
}
