import { PageHeading } from "../../components/shared/PageHeading";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { StoryBlock } from "../../components/bi/StoryBlock";
import { HealthCards, type HealthCard } from "../../components/bi/HealthCards";
import { useAggregation } from "../../hooks/useAggregation";

type GovernanceRow = {
  label: string;
  value: string;
  sub?: string;
  status: "ok" | "warn" | "crit";
};

export function GovernanceRoute() {
  const health = useAggregation<GovernanceRow>("governance_health");
  const rows = health.data?.data ?? [];
  const cards: HealthCard[] = rows.map((r) => ({
    label: r.label,
    value: r.value,
    sub: r.sub,
    status: r.status
  }));

  return (
    <div className="route-stack">
      <PageHeading
        eyebrow="BI / Governança"
        title="Saúde do dataset e cobertura de rotulagem"
        emphasis="saúde"
      />
      <StoryBlock lead="O dashboard é confiável?">
        Antes de interpretar gráficos, confira <b>frescor</b>, <b>cobertura ML</b> e{" "}
        <b>reconciliação camadas</b>. Indicadores críticos bloqueiam insights — trate como{" "}
        <b>pré-condição</b>.
      </StoryBlock>
      {cards.length > 0 ? (
        <HealthCards cards={cards} />
      ) : (
        <section className="card">
          <p className="card-sub">Sem dados de governança disponíveis.</p>
        </section>
      )}
      <AssistantCta area="Governança" />
    </div>
  );
}
