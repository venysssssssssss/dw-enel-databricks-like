import { useFiltersStore } from "../../state/filters-store";

export type RegionScope = "ALL" | "CE" | "SP";

const OPTIONS: { id: RegionScope; label: string; hint: string }[] = [
  { id: "SP", label: "SP", hint: "Foco principal" },
  { id: "CE", label: "CE", hint: "Visão CE" },
  { id: "ALL", label: "Todas", hint: "CE + SP" }
];

export function useRegionScope(): RegionScope {
  const regions = useFiltersStore((state) => state.regions);
  if (regions.length === 0) return "ALL";
  if (regions.length === 1 && regions[0] === "SP") return "SP";
  if (regions.length === 1 && regions[0] === "CE") return "CE";
  return "ALL";
}

export function RegionScopeFilter() {
  const scope = useRegionScope();
  const setPartial = useFiltersStore((state) => state.setPartial);

  function pick(next: RegionScope) {
    if (next === "ALL") setPartial({ regions: [] });
    else setPartial({ regions: [next] });
  }

  return (
    <div className="sb-region-filter" role="group" aria-label="Escopo regional">
      <div className="sb-region-head">
        <span className="sb-region-title">Região do MIS / BI</span>
        <span className="sb-region-meta" title="Severidade Alta/Crítica/Demais permanecem em SP">
          SP locked nas telas de severidade
        </span>
      </div>
      <div className="sb-region-pills">
        {OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            className={"sb-region-pill" + (scope === opt.id ? " is-active" : "")}
            data-region={opt.id}
            onClick={() => pick(opt.id)}
            aria-pressed={scope === opt.id}
            title={opt.hint}
          >
            <span className="lbl">{opt.label}</span>
            <span className="hint">{opt.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
