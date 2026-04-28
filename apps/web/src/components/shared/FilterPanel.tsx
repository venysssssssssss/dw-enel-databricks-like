import { useFiltersStore, PERIOD_PRESETS } from "../../state/filters-store";

export function PeriodFilterTop() {
  const { preset, start, end, setPreset, setPartial } = useFiltersStore();
  return (
    <div className="sb-period-top" role="group" aria-label="Período">
      <div className="sb-section">
        <span className="sb-section-title">Período</span>
        <span className="sb-section-badge">{PERIOD_PRESETS.length}</span>
      </div>
      <div className="period-pills" role="group" aria-label="Atalhos de período">
        {PERIOD_PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={"period-pill" + (preset === p.id ? " is-active" : "")}
            onClick={() => setPreset(p.id)}
            aria-pressed={preset === p.id}
            title={p.label}
          >
            <span className="lbl">{p.label}</span>
            <span className="cmd">{p.cmd}</span>
          </button>
        ))}
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
        {start || end ? (
          <button
            type="button"
            className="ghost-button period-clear"
            onClick={() => setPartial({ start: null, end: null })}
          >
            Limpar período
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function FilterPanel() {
  const { refat, setPartial, reset } = useFiltersStore();

  return (
    <>
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
