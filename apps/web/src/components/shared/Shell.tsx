import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useUiStore } from "../../state/ui-store";
import { useFiltersUrlSync } from "../../hooks/useFiltersUrlSync";
import { features } from "../../lib/features";

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
  const navigate = useNavigate();
  const surface = ACONCHEGANTE_ROUTES.has(pathname) ? "aconchegante" : "graphite";

  useFiltersUrlSync();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!features.severidadeV1 || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName.toLowerCase();
      if (tagName === "input" || tagName === "textarea" || target?.isContentEditable) return;
      if (event.key === "2") {
        event.preventDefault();
        void navigate({ to: "/bi/severidade-alta" });
      }
      if (event.key === "3") {
        event.preventDefault();
        void navigate({ to: "/bi/severidade-critica" });
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate]);

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
