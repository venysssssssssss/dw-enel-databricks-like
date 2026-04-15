from __future__ import annotations

from typing import Any

from apps.streamlit.components.narrative import LayerNarrative, layer_intro


def render(st: Any, *, theme: str = "light") -> None:
    del theme
    layer_intro(
        st,
        LayerNarrative(
            icon="🎓",
            title="Sessão Educacional",
            question="Como interpretar corretamente cada camada do dashboard?",
            method="Glossário operacional, regras de leitura e limites conhecidos da IA.",
            action="Use esta página para onboarding de novos analistas e validação com negócio.",
        ),
    )
    st.markdown(
        """
### Fluxo recomendado de análise

1. Comece no **BI MIS Executivo** para entender volume, severidade e região.
2. Vá para **CE · Reclamações Totais** para ver se erro de leitura aparece como causa
   de temas maiores.
3. Use **Ritmo Operacional** para identificar aceleração temporal.
4. Use **Padrões & Concentrações** para transformar tópicos IA em hipóteses operacionais.
5. Use **Impacto de Refaturamento** para priorizar dinheiro e retrabalho.
6. Use **Taxonomia Descoberta** e **Governança** para revisar `indefinido` e melhorar
   o classificador.

### Como ler `indefinido`

`indefinido` significa que o classificador encontrou sinal fraco ou classes empatadas.
Ele deve alimentar uma fila de revisão e enriquecimento da taxonomia.

### Limites conhecidos

- O dashboard não substitui análise técnica da ordem.
- A classificação é determinística por taxonomia e depende da qualidade do texto livre.
- Dados recém-normalizados exigem reprocessamento dos artefatos de tópico para refletir
  novos clusters.
"""
    )
