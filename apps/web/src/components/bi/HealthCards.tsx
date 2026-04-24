export type HealthCard = {
  label: string;
  value: string;
  sub?: string;
  status: "ok" | "warn" | "crit";
};

export function HealthCards({ cards }: { cards: HealthCard[] }) {
  return (
    <section className="health-grid" aria-label="Indicadores de saúde operacional">
      {cards.map((card) => (
        <article className={`health-card is-${card.status}`} key={card.label}>
          <span className="label">{card.label}</span>
          <span className="value">{card.value}</span>
          {card.sub ? <span className="sub">{card.sub}</span> : null}
        </article>
      ))}
    </section>
  );
}
