export type Kpi = {
  label: string;
  value: string | number;
  tag?: string;
  sub?: string;
  dominant?: boolean;
  /** Optional full-text title for hover when value/sub are truncated. */
  title?: string;
};

export function KpiStrip({ items }: { items: Kpi[] }) {
  return (
    <section className="kpi-strip" aria-label="KPIs selecionados">
      {items.map((item) => {
        const valueStr = String(item.value ?? "");
        const fullTitle = item.title ?? `${item.label}: ${valueStr}${item.sub ? " · " + item.sub : ""}`;
        return (
          <article
            key={item.label}
            className={"kpi-tile" + (item.dominant ? " is-dominant" : "")}
            title={fullTitle}
          >
            {item.tag ? <span className="kpi-tag">{item.tag}</span> : null}
            <span className="kpi-label">{item.label}</span>
            <span className="kpi-val" title={valueStr}>
              {item.value}
            </span>
            {item.sub ? (
              <span className="kpi-sub" title={item.sub}>
                {item.sub}
              </span>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
