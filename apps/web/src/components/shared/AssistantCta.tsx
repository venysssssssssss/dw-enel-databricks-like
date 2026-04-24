import { Link } from "@tanstack/react-router";

export function AssistantCta({ area }: { area: string }) {
  const hint = encodeURIComponent(area);
  return (
    <section className="assistant-cta">
      <p>
        Precisa aprofundar nessa área? Leve para o <b>Assistente ENEL</b> com o contexto de{" "}
        <b>{area}</b>.
      </p>
      <Link to="/chat" search={{ context: hint } as never} className="cta-btn">
        Abrir no chat →
      </Link>
    </section>
  );
}
