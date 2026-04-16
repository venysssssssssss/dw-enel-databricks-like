type Kpi = {
  label: string;
  value: string | number;
  detail?: string;
};

export function KpiStrip({ items }: { items: Kpi[] }) {
  return (
    <section className="kpi-strip" aria-label="KPIs selecionados">
      {items.map((item) => (
        <article className="kpi-tile" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.detail ? <small>{item.detail}</small> : null}
        </article>
      ))}
    </section>
  );
}
