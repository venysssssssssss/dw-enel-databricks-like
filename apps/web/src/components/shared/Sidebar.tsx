import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { FilterPanel } from "./FilterPanel";
import { features } from "../../lib/features";
import { EnelLogo } from "./EnelLogo";

type Section = "assistente" | "severidade" | "bi" | "governo";
type NavItem = {
  to: string;
  label: string;
  hint?: string;
  kbd?: string;
  section: Section;
  sev?: "alta" | "critica" | "executivo";
};

const NAV: NavItem[] = [
  { to: "/chat", label: "Assistente RAG", hint: "Copiloto operacional", kbd: "C", section: "assistente" },
  { to: "/bi/mis", label: "MIS Executivo", hint: "Visão consolidada", kbd: "1", section: "severidade", sev: "executivo" },
  { to: "/bi/severidade-alta", label: "Severidade Alta", hint: "Pressão operacional", kbd: "2", section: "severidade", sev: "alta" },
  { to: "/bi/severidade-critica", label: "Severidade Crítica", hint: "Alto impacto financeiro", kbd: "3", section: "severidade", sev: "critica" },
  { to: "/bi/executive", label: "Ritmo", hint: "Tendência mensal", kbd: "5", section: "bi" },
  { to: "/bi/patterns", label: "Padrões", hint: "BERTopic + clusters", kbd: "6", section: "bi" },
  { to: "/bi/impact", label: "Impacto", hint: "Valor reclamado", kbd: "7", section: "bi" },
  { to: "/bi/taxonomy", label: "Taxonomia", hint: "Causas canônicas", kbd: "8", section: "bi" },
  { to: "/bi/governance", label: "Governança", hint: "Qualidade de dados", kbd: "9", section: "governo" },
  { to: "/bi/educational", label: "Educação", hint: "Onboarding", kbd: "0", section: "governo" }
];

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navRef = useRef<HTMLElement | null>(null);
  const itemRefs = useRef(new Map<string, HTMLDivElement>());
  const [activeFrame, setActiveFrame] = useState({ top: 0, height: 0, visible: false });
  const nav = features.severidadeV1
    ? NAV
    : NAV.filter((item) => item.to !== "/bi/severidade-alta" && item.to !== "/bi/severidade-critica");

  const groups: { id: Section; title: string; badge: string }[] = [
    { id: "assistente", title: "Assistente", badge: "RAG" },
    { id: "severidade", title: "Severidade", badge: String(nav.filter((n) => n.section === "severidade").length) },
    { id: "bi", title: "BI · MIS", badge: String(nav.filter((n) => n.section === "bi").length) },
    { id: "governo", title: "Governo", badge: String(nav.filter((n) => n.section === "governo").length) }
  ];

  useEffect(() => {
    const active = itemRefs.current.get(pathname);
    const container = navRef.current;
    if (!active || !container) {
      setActiveFrame((current) => ({ ...current, visible: false }));
      return;
    }
    setActiveFrame({
      top: active.offsetTop,
      height: active.offsetHeight,
      visible: true
    });
  }, [pathname, nav.length]);

  function registerItem(path: string, node: HTMLDivElement | null) {
    if (node) {
      itemRefs.current.set(path, node);
    } else {
      itemRefs.current.delete(path);
    }
  }

  return (
    <aside className="sidebar enel-sidebar" aria-label="Navegação principal">
      <div className="sb-brand-block">
        <div className="sb-brand">
          <EnelLogo size={36} variant="mark" />
          <div className="sb-brand-text">
            <span className="sb-brand-name">ENEL Brasil</span>
            <span className="sb-brand-sub">Analytics · MIS</span>
          </div>
          <span className="sb-brand-version" title="Versão da plataforma">v3.1</span>
        </div>
        <div className="sb-status" role="status">
          <span className="sb-status-dot" aria-hidden />
          <span className="sb-status-label">Operacional</span>
          <span className="sb-status-sep" aria-hidden>·</span>
          <span className="sb-status-region">SP</span>
        </div>
      </div>

      <nav className="sb-nav-scroll" aria-label="Seções" ref={navRef}>
        <span
          className={`sb-active-rail ${activeFrame.visible ? "is-visible" : ""}`}
          style={{
            height: activeFrame.height,
            transform: `translateY(${activeFrame.top}px)`
          }}
          aria-hidden
        />
        {groups.map((g) => {
          const items = nav.filter((n) => n.section === g.id);
          if (!items.length) return null;
          return (
            <SidebarSection key={g.id} title={g.title} badge={g.badge}>
              <div className="nav">
                {items.map((item) => (
                  <div
                    className="nav-item-frame"
                    key={item.to}
                    ref={(node) => registerItem(item.to, node)}
                  >
                    <NavLink item={item} active={pathname === item.to} />
                  </div>
                ))}
              </div>
            </SidebarSection>
          );
        })}

        <div className="sb-divider" aria-hidden />
        <FilterPanel />
      </nav>

      <div className="sb-footer">
        <div className="sb-footer-meta">
          <span className="sb-footer-label">Lakehouse</span>
          <span className="sb-footer-value">MinIO · Iceberg · Trino</span>
        </div>
        <div className="sb-footer-meta">
          <span className="sb-footer-label">Ambiente</span>
          <span className="sb-footer-value">prod-mirror · CPU-only</span>
        </div>
      </div>
    </aside>
  );
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const cls = ["nav-item"];
  if (active) cls.push("is-active");
  if (item.sev) cls.push(`is-sev-${item.sev}`);
  return (
    <Link to={item.to} className={cls.join(" ")} data-sev-nav={item.sev}>
      <span className="nav-dot" aria-hidden />
      <span className="nav-body">
        <span className="nav-label">{item.label}</span>
        {item.hint ? <span className="nav-hint">{item.hint}</span> : null}
      </span>
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
    <div className="sb-group">
      <div className="sb-section">
        <span className="sb-section-title">{title}</span>
        {badge ? <span className="sb-section-badge">{badge}</span> : null}
      </div>
      {children}
    </div>
  );
}
