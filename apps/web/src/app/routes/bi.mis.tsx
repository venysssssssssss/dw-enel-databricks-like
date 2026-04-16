import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars } from "../../components/bi/Charts";
import { useAggregation } from "../../hooks/useAggregation";

type MisRow = {
  regiao: string;
  volume_total: number;
  taxa_refaturamento: number;
  cobertura_rotulo: number;
  causa_dominante: string;
  share_critico: number;
};

export function MisRoute() {
  const mis = useAggregation<MisRow>("mis");
  const rows = mis.data?.data ?? [];
  const total = rows.reduce((sum, row) => sum + Number(row.volume_total ?? 0), 0);
  const top = rows[0];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>BI MIS Executivo</p>
        <h1>Volume, cobertura e severidade por região</h1>
      </section>
      <KpiStrip
        items={[
          { label: "Volume filtrado", value: total },
          { label: "Região principal", value: top?.regiao ?? "..." },
          {
            label: "Causa dominante",
            value: top?.causa_dominante ?? "..."
          }
        ]}
      />
      <section className="chart-section">
        <div>
          <h2>Volume por região</h2>
          <p>Base atual do dataset versionado.</p>
        </div>
        <VolumeBars data={rows} xKey="regiao" yKey="volume_total" />
      </section>
      <DataTable rows={rows} />
    </div>
  );
}

function DataTable({ rows }: { rows: MisRow[] }) {
  return (
    <section className="table-section">
      <h2>Resumo regional</h2>
      <table>
        <thead>
          <tr>
            <th>Região</th>
            <th>Ordens</th>
            <th>Refaturamento</th>
            <th>Cobertura</th>
            <th>Crítico</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.regiao}>
              <td>{row.regiao}</td>
              <td>{row.volume_total}</td>
              <td>{(row.taxa_refaturamento * 100).toFixed(1)}%</td>
              <td>{(row.cobertura_rotulo * 100).toFixed(1)}%</td>
              <td>{(row.share_critico * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
