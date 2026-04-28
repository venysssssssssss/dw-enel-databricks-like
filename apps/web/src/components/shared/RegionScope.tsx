import { useFiltersStore } from "../../state/filters-store";

export type RegionScope = "ALL" | "CE" | "SP";

type RegionStatus = "live" | "preview" | "roadmap";

type RegionOption = {
  id: RegionScope | "RJ";
  label: string;
  status: RegionStatus;
  selectable: boolean;
};

const REGION_OPTIONS: RegionOption[] = [
  { id: "SP", label: "SP", status: "live", selectable: true },
  { id: "CE", label: "CE", status: "live", selectable: true },
  { id: "ALL", label: "Todas", status: "live", selectable: true },
  { id: "RJ", label: "RJ", status: "roadmap", selectable: false }
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

  function pick(opt: RegionOption) {
    if (!opt.selectable) return;
    if (opt.id === "ALL") setPartial({ regions: [] });
    else setPartial({ regions: [opt.id as string] });
  }

  return (
    <div className="sb-region-filter sb-region-filter--compact" role="group" aria-label="Escopo regional">
      <div className="sb-region-pills">
        {REGION_OPTIONS.map((opt) => {
          const active = opt.selectable && scope === opt.id;
          const className =
            "sb-region-pill" +
            (active ? " is-active" : "") +
            (!opt.selectable ? " is-roadmap" : "") +
            (opt.status === "live" ? " is-live" : "");
          return (
            <button
              key={opt.id}
              type="button"
              className={className}
              data-region={opt.id}
              data-status={opt.status}
              onClick={() => pick(opt)}
              aria-pressed={active}
              aria-disabled={!opt.selectable}
              disabled={!opt.selectable}
            >
              <span className="lbl">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
