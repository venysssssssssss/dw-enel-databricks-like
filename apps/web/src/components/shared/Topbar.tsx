import { useRouterState } from "@tanstack/react-router";
import { useDatasetVersion } from "../../hooks/useDatasetVersion";
import { useUiStore } from "../../state/ui-store";

const CRUMB_MAP: Record<string, [string, string]> = {
  "/chat": ["Assistente", "RAG · streaming"],
  "/bi/mis": ["BI", "MIS Executivo"],
  "/bi/ce-totais": ["BI", "CE Totais"],
  "/bi/executive": ["BI", "Ritmo Operacional"],
  "/bi/patterns": ["BI", "Padrões"],
  "/bi/impact": ["BI", "Impacto"],
  "/bi/taxonomy": ["BI", "Taxonomia"],
  "/bi/governance": ["Governo", "Governança"],
  "/bi/educational": ["Governo", "Sessão Educacional"]
};

export function Topbar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { theme, setTheme, toggleSidebar } = useUiStore();
  const version = useDatasetVersion();
  const [parent, leaf] = CRUMB_MAP[pathname] ?? ["", ""];

  return (
    <header className="topbar">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button type="button" className="ghost-button" onClick={toggleSidebar} aria-label="Alternar sidebar">
          ☰
        </button>
        <div className="crumbs">
          {parent} / <b>{leaf}</b>
        </div>
      </div>
      <div className="topbar-actions">
        <span className="sync-status" title="Dataset version">
          <span>Dataset</span>
          <code>{version.data?.hash.slice(0, 10) ?? "…"}</code>
        </span>
        <button
          type="button"
          className="ghost-button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={`Alternar tema (atual: ${theme})`}
        >
          {theme === "dark" ? "☀ Claro" : "☾ Escuro"}
        </button>
      </div>
    </header>
  );
}
