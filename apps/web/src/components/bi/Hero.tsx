type Props = {
  eyebrow: string;
  title: React.ReactNode;
  description: string;
  metricLabel?: string;
  metricValue?: string | number;
  metricDelta?: string;
};

export function Hero({
  eyebrow,
  title,
  description,
  metricLabel,
  metricValue,
  metricDelta
}: Props) {
  return (
    <section className="hero">
      <div className="hero-grid">
        <div>
          <div className="eyebrow">{eyebrow}</div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {metricLabel && metricValue !== undefined ? (
          <div className="hero-metric">
            <div className="mini">{metricLabel}</div>
            <div className="big">{metricValue}</div>
            {metricDelta ? <div className="delta">{metricDelta}</div> : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
