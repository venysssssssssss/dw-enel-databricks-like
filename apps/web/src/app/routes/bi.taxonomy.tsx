import { PageHeading } from "../../components/shared/PageHeading";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { StoryBlock } from "../../components/bi/StoryBlock";
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
      <PageHeading
        eyebrow="BI / Taxonomia"
        title="Classes, severidade e descrição operacional"
        emphasis="taxonomia"
      />
      <StoryBlock lead="O dicionário de causas canônicas.">
        Toda agregação acima depende deste mapa. Severidade e peso são herdados pelos{" "}
        <b>scores de criticidade</b>. Divergências aqui se propagam para dashboards — trate como{" "}
        <b>fonte única</b>.
      </StoryBlock>
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
                <td>
                  <b>{row["Causa canonica"]}</b>
                </td>
                <td>{row.Categoria}</td>
                <td>{row.Severidade}</td>
                <td>{row.Peso}</td>
                <td>{row.Descricao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <AssistantCta area="Taxonomia" />
    </div>
  );
}
