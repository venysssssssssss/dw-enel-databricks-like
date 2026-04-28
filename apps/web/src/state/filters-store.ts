import { create } from "zustand";

export type FilterPreset =
  | "manual"
  | "last_1m"
  | "last_3m"
  | "last_6m"
  | "last_12m"
  | "ce_group"
  | "refat";

export const PERIOD_PRESETS: { id: FilterPreset; label: string; days: number; cmd: string }[] = [
  { id: "last_1m", label: "Último mês", days: 30, cmd: "1" },
  { id: "last_3m", label: "Últimos 3 meses", days: 90, cmd: "3" },
  { id: "last_6m", label: "Últimos 6 meses", days: 180, cmd: "6" },
  { id: "last_12m", label: "Últimos 12 meses", days: 365, cmd: "Y" }
];

export type DashboardFilters = {
  regions: string[];
  causes: string[];
  topics: string[];
  start: string | null; // ISO date YYYY-MM-DD
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

function isoMinusDays(days: number): string {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return start.toISOString().slice(0, 10);
}

function applyPreset(state: FilterState, preset: FilterPreset): Partial<FilterState> {
  if (preset === "manual") {
    return { ...DEFAULT_FILTERS, preset };
  }
  const period = PERIOD_PRESETS.find((p) => p.id === preset);
  if (period) {
    return {
      ...state,
      start: isoMinusDays(period.days),
      end: new Date().toISOString().slice(0, 10),
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

const ALL_PRESETS: FilterPreset[] = [
  "manual",
  "last_1m",
  "last_3m",
  "last_6m",
  "last_12m",
  "ce_group",
  "refat"
];

/** Serialize non-default fields to URL params (user-facing keys). */
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
  const rawPreset = (search.get("preset") ?? "manual") as FilterPreset;
  const preset: FilterPreset = ALL_PRESETS.includes(rawPreset) ? rawPreset : "manual";
  return {
    regions: split("regiao"),
    causes: split("causa"),
    topics: split("topico"),
    start: search.get("inicio") || null,
    end: search.get("fim") || null,
    refat: search.get("refat") === "1",
    total: search.get("total") === "1",
    preset
  };
}

/** API filter contract consumed by /v1/aggregations. */
export function filtersToApiContract(filters: DashboardFilters): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (filters.regions.length) payload.regiao = filters.regions;
  if (filters.causes.length) payload.causa_canonica = filters.causes;
  if (filters.topics.length) payload.topic_name = filters.topics;
  if (filters.start) payload.start_date = filters.start;
  if (filters.end) payload.end_date = filters.end;
  if (filters.refat) payload.flag_resolvido_com_refaturamento = true;
  if (filters.total) payload.include_total = true;
  return payload;
}

const PRESET_LABELS: Record<FilterPreset, string> = {
  manual: "Manual",
  last_1m: "1 mês",
  last_3m: "3 meses",
  last_6m: "6 meses",
  last_12m: "12 meses",
  ce_group: "CE",
  refat: "Refaturamento"
};

export function presetLabel(preset: FilterPreset): string {
  return PRESET_LABELS[preset] ?? "Manual";
}

export function activeFilterChips(filters: DashboardFilters): string[] {
  const chips: string[] = [];
  if (filters.regions.length) chips.push(`Região: ${filters.regions.join(", ")}`);
  if (filters.causes.length) chips.push(`Causas: ${filters.causes.length} selecionadas`);
  if (filters.topics.length) chips.push(`Tópicos: ${filters.topics.length} selecionados`);
  if (filters.preset !== "manual" && PERIOD_PRESETS.some((p) => p.id === filters.preset)) {
    chips.push(`Período: ${presetLabel(filters.preset)}`);
  } else if (filters.start || filters.end) {
    chips.push(`Período: ${filters.start ?? "início"} → ${filters.end ?? "fim"}`);
  }
  if (filters.refat) chips.push("Somente refaturamento");
  return chips;
}
