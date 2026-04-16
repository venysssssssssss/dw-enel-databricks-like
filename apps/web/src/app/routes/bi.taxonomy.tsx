import { useAggregation } from "../../hooks/useAggregation";

type Taxonomy = {
  "Causa canonica": string;
  Categoria: string;
  Severidade: string;
  Peso: number;
  Descricao: string;
};

export function TaxonomyRoute() {
  const taxonomy = useAggregation<Taxonomy>("taxonomy_reference");
  const rows = taxonomy.data?.data ?? [];

  return (
    <div className="route-stack">
      <section className="page-heading">
        <p>Taxonomia</p>
        <h1>Classes, severidade e descrição operacional</h1>
      </section>
      <section className="table-section">
        <table>
          <thead>
            <tr>
              <th>Causa</th>
              <th>Categoria</th>
              <th>Severidade</th>
              <th>Peso</th>
              <th>Descrição</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row["Causa canonica"]}>
                <td>{row["Causa canonica"]}</td>
                <td>{row.Categoria}</td>
                <td>{row.Severidade}</td>
                <td>{row.Peso}</td>
                <td>{row.Descricao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
