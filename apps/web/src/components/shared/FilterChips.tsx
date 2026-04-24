import { useFiltersStore, activeFilterChips } from "../../state/filters-store";

export function FilterChips() {
  const filters = useFiltersStore();
  const chips = activeFilterChips(filters);
  if (chips.length === 0) {
    return (
      <div className="filter-chips-bar">
        <span style={{ opacity: 0.7 }}>Sem filtros restritivos</span>
      </div>
    );
  }
  return (
    <div className="filter-chips-bar">
      {chips.map((chip) => (
        <span key={chip} className="chip is-on">
          {chip}
        </span>
      ))}
    </div>
  );
}
