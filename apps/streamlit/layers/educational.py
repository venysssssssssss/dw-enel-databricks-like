from __future__ import annotations

from typing import Any

from apps.streamlit.components.narrative import LayerNarrative, layer_intro
from apps.streamlit.layers.common import render_assistant_cta


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
<div class="enel-card" style="padding:18px 20px;margin-bottom:14px">
  <h2 style="font-size:17px;margin:0 0 10px;color:var(--text)">Fluxo recomendado</h2>
  <div class="enel-story-steps">
    <div class="enel-story-step"><span class="n">1</span>BI MIS: volume, severidade e região.</div>
    <div class="enel-story-step"><span class="n">2</span>CE Totais: temas e cruzamentos.</div>
    <div class="enel-story-step"><span class="n">3</span>Ritmo: aceleração temporal.</div>
    <div class="enel-story-step"><span class="n">4</span>Padrões: causa, região e tópico IA.</div>
    <div class="enel-story-step"><span class="n">5</span>Impacto: dinheiro e retrabalho.</div>
    <div class="enel-story-step"><span class="n">6</span>Governança: revisão.</div>
  </div>
</div>
<div class="enel-card" style="padding:18px 20px;margin-bottom:14px">
  <h2 style="font-size:17px;margin:0 0 8px;color:var(--text)">Glossário operacional</h2>
  <div class="enel-insight" style="margin-top:0"><span class="label">indefinido</span>
    Sinal fraco ou classes empatadas; deve alimentar fila de revisão e enriquecimento.
  </div>
  <div class="enel-insight"><span class="label">reincidência</span>
    Instalação anonimizada com múltiplas ordens no período filtrado.
  </div>
  <div class="enel-insight"><span class="label">refaturamento</span>
    Proxy de retrabalho financeiro, não substitui validação técnica da ordem.
  </div>
</div>
<div class="enel-card" style="padding:18px 20px">
  <h2 style="font-size:17px;margin:0 0 8px;color:var(--text)">Limites conhecidos</h2>
  <div class="enel-story-body">
    <p>O dashboard não substitui análise técnica da ordem.</p>
    <p>A classificação é determinística por taxonomia e depende da qualidade do texto livre.</p>
    <p>Dados recém-normalizados exigem reprocessamento dos artefatos de tópico.</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    render_assistant_cta(st, area="Sessão Educacional", key="cta_assistente_educacional")
