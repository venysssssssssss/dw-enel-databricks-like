import { PageHeading } from "../../components/shared/PageHeading";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { StoryBlock } from "../../components/bi/StoryBlock";

export function EducationalRoute() {
  return (
    <div className="route-stack">
      <PageHeading
        eyebrow="BI / Sessão Educacional"
        title="Como ler este dashboard"
        emphasis="como ler"
      />
      <StoryBlock lead="A jornada analítica em três camadas.">
        Todo número parte de <b>ordens brutas</b>, passa por <b>classificação canônica</b>,
        agrega em <b>métricas de desfecho</b>. Entenda o caminho antes de confiar no agregado.
      </StoryBlock>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">1. MIS Executivo — o pulso</h2>
            <p className="card-sub">Volume, líder regional, cobertura ML.</p>
          </div>
        </div>
        <p>
          Comece aqui. Identifica <b>onde</b> (região) e <b>o quê</b> (causa dominante).
          Cobertura ML indica se a rotulagem automática é confiável.
        </p>
      </section>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">2. Padrões e Impacto — o porquê</h2>
            <p className="card-sub">Tópicos descobertos + taxa de refaturamento.</p>
          </div>
        </div>
        <p>
          Padrões revelam narrativas não codificadas. Impacto mede o custo real: refaturamento é
          o sinal terminal de erro. Cruze <b>volume absoluto</b> com <b>taxa</b> — nunca um sem o
          outro.
        </p>
      </section>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">3. CE e Taxonomia — a linguagem</h2>
            <p className="card-sub">Vocabulário operacional compartilhado.</p>
          </div>
        </div>
        <p>
          Reclamações CE conectam a voz do cliente às ordens operacionais. Taxonomia é o
          dicionário — toda severidade e peso herdam dela.
        </p>
      </section>
      <section className="card">
        <div className="card-head">
          <div>
            <h2 className="card-title">4. Governança — a pré-condição</h2>
            <p className="card-sub">Antes de interpretar, valide.</p>
          </div>
        </div>
        <p>
          Frescor do dataset, cobertura ML, reconciliação entre camadas. Indicadores críticos
          aqui bloqueiam a leitura dos demais painéis.
        </p>
      </section>
      <AssistantCta area="Sessão Educacional" />
    </div>
  );
}
