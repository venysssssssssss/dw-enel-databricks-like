export type Kpi = {
  label: string;
  value: string | number;
  tag?: string;
  sub?: string;
  dominant?: boolean;
};

export function KpiStrip({ items }: { items: Kpi[] }) {
  return (
    <section className="kpi-strip" aria-label="KPIs selecionados">
      {items.map((item) => (
        <article
          key={item.label}
          className={item.dominant ? "kpi-tile is-dominant" : "kpi-tile"}
        >
          {item.tag ? <span className="kpi-tag">{item.tag}</span> : null}
          <span className="kpi-label">{item.label}</span>
          <span className="kpi-val">{item.value}</span>
          {item.sub ? <span className="kpi-sub">{item.sub}</span> : null}
        </article>
      ))}
    </section>
  );
}
