import { useFiltersStore } from "../../state/filters-store";

export type RegionScope = "ALL" | "CE" | "SP";

type RegionStatus = "live" | "preview" | "roadmap";

type RegionOption = {
  id: RegionScope | "RJ" | "MG" | "GO";
  label: string;
  hint: string;
  status: RegionStatus;
  selectable: boolean;
};

const REGION_OPTIONS: RegionOption[] = [
  { id: "SP", label: "SP", hint: "Base demonstrativa · dados reais", status: "live", selectable: true },
  { id: "CE", label: "CE", hint: "Visão CE · disponível em /chat e BI", status: "live", selectable: true },
  { id: "ALL", label: "Todas", hint: "CE + SP no mesmo recorte", status: "live", selectable: true },
  { id: "RJ", label: "RJ", hint: "Em implantação · sem carga ainda", status: "roadmap", selectable: false },
  { id: "MG", label: "MG", hint: "Em implantação · sem carga ainda", status: "roadmap", selectable: false },
  { id: "GO", label: "GO", hint: "Em implantação · sem carga ainda", status: "roadmap", selectable: false }
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
    <div className="sb-region-filter" role="group" aria-label="Escopo regional">
      <div className="sb-region-head">
        <span className="sb-region-title">Regional · roadmap</span>
        <span className="sb-region-meta" title="Severidade Alta/Crítica/Demais permanecem em SP">
          Severidade fixa em SP
        </span>
      </div>
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
              title={opt.hint}
            >
              <span className="lbl">{opt.label}</span>
              <span className="hint">{opt.hint}</span>
              {opt.status === "roadmap" ? (
                <span className="status-badge" aria-hidden>
                  em breve
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <p className="sb-region-note">
        Hoje a base demonstrativa é <b>SP</b>. CE é visão complementar de reclamações totais.
        Outras regionais entram conforme novas cargas regionais ficam disponíveis — a arquitetura
        já suporta a expansão.
      </p>
    </div>
  );
}
