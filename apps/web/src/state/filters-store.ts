import { create } from "zustand";

export type FilterPreset = "manual" | "last30" | "ce_group" | "refat";

export type DashboardFilters = {
  regions: string[];
  causes: string[];
  topics: string[];
  start: string | null; // ISO date
  end: string | null;
  refat: boolean;
  total: boolean;
  preset: FilterPreset;
};

export const DEFAULT_FILTERS: DashboardFilters = {
  regions: [],
  causes: [],
  topics: [],
  start: null,
  end: null,
  refat: false,
  total: false,
  preset: "manual"
};

type FilterState = DashboardFilters & {
  setPartial: (patch: Partial<DashboardFilters>) => void;
  setPreset: (preset: FilterPreset) => void;
  reset: () => void;
  hydrate: (filters: Partial<DashboardFilters>) => void;
};

export const useFiltersStore = create<FilterState>((set) => ({
  ...DEFAULT_FILTERS,
  setPartial: (patch) => set((state) => ({ ...state, ...patch, preset: "manual" })),
  setPreset: (preset) => set((state) => applyPreset(state, preset)),
  reset: () => set({ ...DEFAULT_FILTERS }),
  hydrate: (filters) => set((state) => ({ ...state, ...filters }))
}));

function applyPreset(state: FilterState, preset: FilterPreset): Partial<FilterState> {
  if (preset === "manual") {
    return { ...DEFAULT_FILTERS, preset };
  }
  if (preset === "last30") {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    return {
      ...state,
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
      refat: false,
      preset
    };
  }
  if (preset === "ce_group") {
    return { ...state, regions: ["CE"], refat: false, preset };
  }
  if (preset === "refat") {
    return { ...state, refat: true, preset };
  }
  return state;
}

/** Serialize non-default fields to URL params. */
export function filtersToQueryParams(filters: DashboardFilters): Record<string, string> {
  const out: Record<string, string> = {};
  if (filters.regions.length) out.regiao = filters.regions.join(",");
  if (filters.causes.length) out.causa = filters.causes.join(",");
  if (filters.topics.length) out.topico = filters.topics.join(",");
  if (filters.start) out.inicio = filters.start;
  if (filters.end) out.fim = filters.end;
  if (filters.refat) out.refat = "1";
  if (filters.total) out.total = "1";
  if (filters.preset !== "manual") out.preset = filters.preset;
  return out;
}

export function filtersFromQueryParams(search: URLSearchParams): Partial<DashboardFilters> {
  const split = (key: string): string[] =>
    (search.get(key) ?? "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  const preset = (search.get("preset") ?? "manual") as FilterPreset;
  return {
    regions: split("regiao"),
    causes: split("causa"),
    topics: split("topico"),
    start: search.get("inicio") || null,
    end: search.get("fim") || null,
    refat: search.get("refat") === "1",
    total: search.get("total") === "1",
    preset: ["manual", "last30", "ce_group", "refat"].includes(preset) ? preset : "manual"
  };
}

/** API filter contract consumed by /v1/aggregations. */
export function filtersToApiContract(filters: DashboardFilters): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (filters.regions.length) payload.regiao = filters.regions;
  if (filters.causes.length) payload.causa_canonica = filters.causes;
  if (filters.topics.length) payload.topic_name = filters.topics;
  if (filters.start) payload.inicio = filters.start;
  if (filters.end) payload.fim = filters.end;
  if (filters.refat) payload.flag_resolvido_com_refaturamento = true;
  if (filters.total) payload.include_total = true;
  return payload;
}

export function activeFilterChips(filters: DashboardFilters): string[] {
  const chips: string[] = [];
  if (filters.regions.length) chips.push(`Região: ${filters.regions.join(", ")}`);
  if (filters.causes.length) chips.push(`Causas: ${filters.causes.length} selecionadas`);
  if (filters.topics.length) chips.push(`Tópicos: ${filters.topics.length} selecionados`);
  if (filters.start || filters.end) {
    chips.push(`Período: ${filters.start ?? "início"} → ${filters.end ?? "fim"}`);
  }
  if (filters.refat) chips.push("Somente refaturamento");
  return chips;
}
