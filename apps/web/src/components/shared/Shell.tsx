import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useDatasetVersion } from "../../hooks/useDatasetVersion";
import { useUiStore } from "../../state/ui-store";

const nav = [
  { to: "/chat", label: "Assistente" },
  { to: "/bi/mis", label: "MIS" },
  { to: "/bi/executive", label: "Ritmo" },
  { to: "/bi/patterns", label: "Padrões" },
  { to: "/bi/impact", label: "Impacto" },
  { to: "/bi/taxonomy", label: "Taxonomia" }
];

export function Shell({ children }: { children: ReactNode }) {
  const { sidebarOpen, toggleSidebar, theme, setTheme } = useUiStore();
  const version = useDatasetVersion();
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className={sidebarOpen ? "sidebar" : "sidebar sidebar--closed"}>
        <div className="brand">
          <span className="brand-mark">E</span>
          <div>
            <strong>ENEL Analytics</strong>
            <small>Erros de leitura</small>
          </div>
        </div>
        <nav aria-label="Principal">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={pathname === item.to ? "nav-link nav-link--active" : "nav-link"}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <img
          className="operation-image"
          src="https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&w=640&q=80"
          alt="Infraestrutura elétrica em operação"
        />
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button type="button" className="ghost-button" onClick={toggleSidebar}>
            Menu
          </button>
          <div className="sync-status">
            <span>Dataset</span>
            <code>{version.data?.hash.slice(0, 10) ?? "carregando"}</code>
          </div>
          <button
            type="button"
            className="ghost-button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "Claro" : "Escuro"}
          </button>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
