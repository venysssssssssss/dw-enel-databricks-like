import { TrendLine, VolumeBars } from "../../components/bi/Charts";
import { useAggregation } from "../../hooks/useAggregation";

type MonthlyRow = {
  mes_ingresso: string;
  regiao: string;
  qtd_erros: number;
  mom: number;
};

type CauseRow = {
  causa_canonica: string;
  qtd_erros: number;
  percentual: number;
};

export function ExecutiveRoute() {
  const monthly = useAggregation<MonthlyRow>("mis_monthly_mis");
  const causes = useAggregation<CauseRow>("root_cause_distribution");
  const monthlyRows = monthly.data?.data ?? [];
  const causeRows = causes.data?.data ?? [];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>Ritmo Operacional</p>
        <h1>Série mensal e causas mais frequentes</h1>
      </section>
      <section className="split-section">
        <div>
          <h2>Evolução mensal</h2>
          <TrendLine data={monthlyRows} xKey="mes_ingresso" yKey="qtd_erros" />
        </div>
        <div>
          <h2>Causas</h2>
          <VolumeBars data={causeRows} xKey="causa_canonica" yKey="qtd_erros" />
        </div>
      </section>
    </div>
  );
}
