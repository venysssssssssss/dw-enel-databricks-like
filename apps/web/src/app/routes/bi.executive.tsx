import { TrendLine, VolumeBars } from "../../components/bi/Charts";
import { PageHeading } from "../../components/shared/PageHeading";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { FilterChips } from "../../components/shared/FilterChips";
import { useAggregation } from "../../hooks/useAggregation";

type MonthlyRow = { mes_ingresso: string; regiao: string; qtd_erros: number; mom: number };
type CauseRow = { causa_canonica: string; qtd_erros: number; percentual: number };

export function ExecutiveRoute() {
  const monthly = useAggregation<MonthlyRow>("mis_monthly_mis");
  const causes = useAggregation<CauseRow>("root_cause_distribution");

  return (
    <div className="route-stack">
      <PageHeading
        eyebrow="BI / Ritmo Operacional"
        title="Série mensal e causas mais frequentes"
        emphasis="aceleração"
      />
      <FilterChips />
      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2 className="card-title">Evolução mensal</h2>
          </div>
          <TrendLine data={monthly.data?.data ?? []} xKey="mes_ingresso" yKey="qtd_erros" />
        </section>
        <section className="card">
          <div className="card-head">
            <h2 className="card-title">Causas principais</h2>
          </div>
          <VolumeBars data={causes.data?.data ?? []} xKey="causa_canonica" yKey="qtd_erros" />
        </section>
      </div>
      <AssistantCta area="Ritmo Operacional" />
    </div>
  );
}
