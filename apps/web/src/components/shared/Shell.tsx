import { useRouterState } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useUiStore } from "../../state/ui-store";
import { useFiltersUrlSync } from "../../hooks/useFiltersUrlSync";

/** Routes rendered with the warm "aconchegante" palette. */
const ACONCHEGANTE_ROUTES = new Set<string>([
  "/bi/mis",
  "/bi/ce-totais",
  "/bi/executive",
  "/bi/impact",
  "/bi/governance",
  "/bi/educational",
  "/bi/severidade-alta",
  "/bi/severidade-critica"
]);

export function Shell({ children }: { children: ReactNode }) {
  const { sidebarOpen, theme } = useUiStore();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const surface = ACONCHEGANTE_ROUTES.has(pathname) ? "aconchegante" : "graphite";

  useFiltersUrlSync();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <div className="app-shell" data-sidebar={sidebarOpen ? "open" : "closed"}>
      <Sidebar />
      <div className="workspace">
        <Topbar />
        <main data-surface={surface}>{children}</main>
      </div>
    </div>
  );
}
