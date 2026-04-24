import { Hero } from "../../components/bi/Hero";
import { KpiStrip } from "../../components/bi/KpiStrip";
import { VolumeBars, TrendLine } from "../../components/bi/Charts";
import { AssistantCta } from "../../components/shared/AssistantCta";
import { FilterChips } from "../../components/shared/FilterChips";
import { StoryBlock } from "../../components/bi/StoryBlock";
import { useAggregation } from "../../hooks/useAggregation";

type MacroRow = {
  macro_tema_label: string;
  qtd: number;
  percentual: number;
};

type TrendRow = {
  ano_mes: string;
  macro_tema_label: string;
  qtd: number;
};

type CrossRow = {
  macro_tema_label: string;
  qtd_com_erro_leitura: number;
  percentual: number;
};

export function CeTotaisRoute() {
  const macro = useAggregation<MacroRow>("ce_macro_distribution");
  const trend = useAggregation<TrendRow>("ce_monthly_trend_by_tema");
  const cross = useAggregation<CrossRow>("ce_cruzamento_erro_leitura");

  const macroRows = macro.data?.data ?? [];
  const trendRows = trend.data?.data ?? [];
  const crossRows = cross.data?.data ?? [];

  const total = macroRows.reduce((s, r) => s + Number(r.qtd ?? 0), 0);
  const dom = [...macroRows].sort((a, b) => b.qtd - a.qtd)[0];

  return (
    <div className="route-stack">
      <Hero
        eyebrow="BI / CE Totais"
        title={
          <>
            Reclamações CE e <em>cruzamento</em> com erro de leitura
          </>
        }
        description="Universo total de reclamações CE, classificado por macrotema. Ligação explícita com o subconjunto que também registra erro de leitura."
        metricLabel="Reclamações CE"
        metricValue={formatNumber(total)}
        metricDelta={dom ? `Tema líder: ${dom.macro_tema_label}` : ""}
      />
      <FilterChips />
      <KpiStrip
        items={[
          { label: "Total CE", value: formatNumber(total), tag: "universo", dominant: true },
          { label: "Temas classificados", value: macroRows.length, tag: "macro" },
          {
            label: "Tema dominante",
            value: dom?.macro_tema_label ?? "…",
            tag: dom ? `${(dom.percentual * 100).toFixed(1)}%` : ""
          }
        ]}
      />
      <StoryBlock lead="O que domina as reclamações CE e como cruza com erro de leitura?">
        A classificação macro agrupa textos livres em categorias operacionais. Use o cruzamento
        para provar <b>causa-raiz indireta</b>: temas CE com alta interseção com erro de leitura
        sinalizam retrabalho sobreposto.
      </StoryBlock>
      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">Macrotemas de reclamações CE</h2>
              <p className="card-sub">Distribuição do universo CE classificado.</p>
            </div>
          </div>
          <VolumeBars data={macroRows} xKey="macro_tema_label" yKey="qtd" />
        </section>
        <section className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">Tendência mensal</h2>
              <p className="card-sub">Evolução temporal para separar volume persistente de pico.</p>
            </div>
          </div>
          <TrendLine data={trendRows} xKey="ano_mes" yKey="qtd" />
        </section>
      </div>
      {crossRows.length > 0 ? (
        <section className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">Cruzamento com erro de leitura</h2>
              <p className="card-sub">
                Percentual de reclamações CE associadas a instalações com erro de leitura.
              </p>
            </div>
          </div>
          <VolumeBars data={crossRows} xKey="macro_tema_label" yKey="qtd_com_erro_leitura" />
        </section>
      ) : null}
      <AssistantCta area="CE Totais" />
    </div>
  );
}

function formatNumber(n: number | string): string {
  return Number(n).toLocaleString("pt-BR");
}
