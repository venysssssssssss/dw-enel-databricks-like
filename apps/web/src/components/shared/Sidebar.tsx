import { Link, useRouterState } from "@tanstack/react-router";
import { FilterPanel } from "./FilterPanel";

type NavItem = {
  to: string;
  label: string;
  kbd?: string;
  section: "assistente" | "bi" | "governo";
};

const NAV: NavItem[] = [
  { to: "/chat", label: "Assistente", kbd: "C", section: "assistente" },
  { to: "/bi/mis", label: "MIS Executivo", kbd: "1", section: "bi" },
  { to: "/bi/ce-totais", label: "CE Totais", kbd: "2", section: "bi" },
  { to: "/bi/executive", label: "Ritmo", kbd: "3", section: "bi" },
  { to: "/bi/patterns", label: "Padrões", kbd: "4", section: "bi" },
  { to: "/bi/impact", label: "Impacto", kbd: "5", section: "bi" },
  { to: "/bi/taxonomy", label: "Taxonomia", kbd: "6", section: "bi" },
  { to: "/bi/governance", label: "Governança", kbd: "7", section: "governo" },
  { to: "/bi/educational", label: "Sessão Educacional", kbd: "8", section: "governo" }
];

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <aside className="sidebar" aria-label="Navegação principal">
      <div className="sb-brand">
        <span className="sb-brand-mark" aria-hidden>
          E
        </span>
        <div className="sb-brand-text">
          <span className="sb-brand-name">ENEL Analytics</span>
          <span className="sb-brand-sub">erros · leitura</span>
        </div>
      </div>

      <SidebarSection title="Assistente" badge="RAG">
        <nav className="nav">
          {NAV.filter((n) => n.section === "assistente").map((item) => (
            <NavLink key={item.to} item={item} active={pathname === item.to} />
          ))}
        </nav>
      </SidebarSection>

      <SidebarSection title="BI / MIS" badge={String(NAV.filter((n) => n.section === "bi").length)}>
        <nav className="nav">
          {NAV.filter((n) => n.section === "bi").map((item) => (
            <NavLink key={item.to} item={item} active={pathname === item.to} />
          ))}
        </nav>
      </SidebarSection>

      <SidebarSection title="Governo" badge="2">
        <nav className="nav">
          {NAV.filter((n) => n.section === "governo").map((item) => (
            <NavLink key={item.to} item={item} active={pathname === item.to} />
          ))}
        </nav>
      </SidebarSection>

      <FilterPanel />
    </aside>
  );
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link to={item.to} className={active ? "nav-item is-active" : "nav-item"}>
      <span className="nav-dot" aria-hidden />
      <span>{item.label}</span>
      {item.kbd ? <span className="nav-kbd">{item.kbd}</span> : null}
    </Link>
  );
}

function SidebarSection({
  title,
  badge,
  children
}: {
  title: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="sb-section">
        <span className="sb-section-title">{title}</span>
        {badge ? <span className="sb-section-badge">{badge}</span> : null}
      </div>
      {children}
    </div>
  );
}
