import { useFiltersStore, type FilterPreset } from "../../state/filters-store";

const PRESETS: { id: FilterPreset; label: string; cmd: string }[] = [
  { id: "manual", label: "Manual", cmd: "1" },
  { id: "last30", label: "Últimos 30 dias", cmd: "2" },
  { id: "ce_group", label: "CE · Grupo operacional", cmd: "3" },
  { id: "refat", label: "Ordens com refaturamento", cmd: "4" }
];

export function FilterPanel() {
  const { preset, refat, start, end, setPreset, setPartial, reset } = useFiltersStore();

  return (
    <>
      <div>
        <div className="sb-section">
          <span className="sb-section-title">Presets</span>
          <span className="sb-section-badge">{PRESETS.length}</span>
        </div>
        <div className="preset-stack">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={p.id === preset ? "preset-item is-active" : "preset-item"}
              onClick={() => setPreset(p.id)}
            >
              <span className="dot" aria-hidden />
              <span>{p.label}</span>
              <span className="cmd">{p.cmd}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="sb-section">
          <span className="sb-section-title">Período</span>
        </div>
        <div className="filter-group">
          <label className="filter-label">
            Início
            <input
              type="date"
              value={start ?? ""}
              onChange={(e) => setPartial({ start: e.target.value || null })}
              style={inputStyle}
            />
          </label>
          <label className="filter-label">
            Fim
            <input
              type="date"
              value={end ?? ""}
              onChange={(e) => setPartial({ end: e.target.value || null })}
              style={inputStyle}
            />
          </label>
        </div>
      </div>

      <div>
        <div className="sb-section">
          <span className="sb-section-title">Preferências</span>
        </div>
        <div className="filter-group">
          <div className="toggle-row">
            <div>
              <div style={{ fontSize: 13, color: "var(--text)" }}>Somente refaturamento</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Filtra flag ACF/ASF</div>
            </div>
            <button
              type="button"
              className={refat ? "sw is-on" : "sw"}
              onClick={() => setPartial({ refat: !refat })}
              aria-pressed={refat}
              aria-label="Somente refaturamento"
            />
          </div>
        </div>
      </div>

      <button
        type="button"
        className="ghost-button"
        style={{ width: "100%", justifyContent: "center" }}
        onClick={reset}
      >
        Limpar filtros
      </button>
    </>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--r-sm)",
  color: "var(--text)",
  padding: "6px 10px",
  fontSize: 12.5,
  fontFamily: "var(--font-mono)"
};
