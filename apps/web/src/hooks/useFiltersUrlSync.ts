import { useEffect, useRef } from "react";
import { useFiltersStore, filtersToQueryParams, filtersFromQueryParams } from "../state/filters-store";

/**
 * Bi-directional URL <-> filter-store sync.
 * Hydrates from `location.search` on mount; writes back via replaceState on change.
 */
export function useFiltersUrlSync() {
  const hydrate = useFiltersStore((s) => s.hydrate);
  const hydrated = useRef(false);

  useEffect(() => {
    if (hydrated.current) return;
    const parsed = filtersFromQueryParams(new URLSearchParams(window.location.search));
    hydrate(parsed);
    hydrated.current = true;
  }, [hydrate]);

  useEffect(() => {
    const unsub = useFiltersStore.subscribe((state) => {
      if (!hydrated.current) return;
      const params = new URLSearchParams(window.location.search);
      // Preserve unrelated params (theme, etc.)
      ["regiao", "causa", "topico", "inicio", "fim", "refat", "total", "preset"].forEach((k) =>
        params.delete(k)
      );
      Object.entries(filtersToQueryParams(state)).forEach(([k, v]) => params.set(k, v));
      const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
      window.history.replaceState(null, "", next);
    });
    return () => unsub();
  }, []);
}
