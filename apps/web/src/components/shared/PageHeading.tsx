type Props = { eyebrow: string; title: string; emphasis?: string };

export function PageHeading({ eyebrow, title, emphasis }: Props) {
  return (
    <section className="page-heading">
      <span className="eyebrow">{eyebrow}</span>
      <h1>
        {title}
        {emphasis ? (
          <>
            {" "}
            <em>{emphasis}</em>
          </>
        ) : null}
      </h1>
    </section>
  );
}
