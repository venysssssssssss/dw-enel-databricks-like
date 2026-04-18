from __future__ import annotations

import pandas as pd

from src.data_plane.views import (
    ce_total_assunto_causa_view,
    motivos_taxonomia_view,
    sp_causas_por_tipo_medidor_view,
)


def test_sp_causas_por_tipo_medidor_view_ranks_top_causes() -> None:
    def _row(
        ordem: str,
        regiao: str,
        tipo: str,
        causa: str,
    ) -> dict[str, str]:
        return {
            "ordem": ordem,
            "regiao": regiao,
            "tipo_medidor_dominante": tipo,
            "causa_canonica": causa,
        }

    frame = pd.DataFrame(
        [
            _row("1", "SP", "Digital", "digitacao"),
            _row("2", "SP", "Digital", "digitacao"),
            _row("3", "SP", "Digital", "autoleitura_cliente"),
            _row("4", "SP", "Digital", "autoleitura_cliente"),
            _row("5", "SP", "Digital", "autoleitura_cliente"),
            _row("6", "SP", "Digital", "impedimento_acesso"),
            _row("7", "SP", "Analógico", "digitacao"),
            _row("8", "SP", "Analógico", "indefinido"),
            _row("9", "CE", "Digital", "digitacao"),
        ]
    )

    out = sp_causas_por_tipo_medidor_view(frame, top_types=2, top_causes_per_type=2)

    assert not out.empty
    assert set(out["regiao"].astype(str)) == {"SP"}
    digital = out.loc[out["tipo_medidor_dominante"] == "Digital"].sort_values("rank")
    assert list(digital["causa_canonica"]) == ["autoleitura_cliente", "digitacao"]
    assert list(digital["rank"]) == [1, 2]
    assert int(digital.iloc[0]["qtd_total_tipo"]) == 6


def test_ce_total_assunto_causa_view_keeps_top_causes_per_topic() -> None:
    def _row(
        ordem: str,
        regiao: str,
        tipo_origem: str,
        assunto: str,
        causa: str,
    ) -> dict[str, str]:
        return {
            "ordem": ordem,
            "regiao": regiao,
            "tipo_origem": tipo_origem,
            "assunto": assunto,
            "causa_canonica": causa,
        }

    frame = pd.DataFrame(
        [
            _row(
                "1",
                "CE",
                "reclamacao_total",
                "REFATURAMENTO PRODUTOS",
                "refaturamento_corretivo",
            ),
            _row(
                "2",
                "CE",
                "reclamacao_total",
                "REFATURAMENTO PRODUTOS",
                "refaturamento_corretivo",
            ),
            _row(
                "3",
                "CE",
                "reclamacao_total",
                "REFATURAMENTO PRODUTOS",
                "consumo_elevado_revisao",
            ),
            _row(
                "4",
                "CE",
                "reclamacao_total",
                "CRITICA GRUPO B - REFATURAMENTO",
                "grupo_tarifario_incorreto",
            ),
            _row("5", "CE", "erro_leitura", "REFATURAMENTO PRODUTOS", "digitacao"),
            _row("6", "SP", "base_n1_sp", "ERRO DE LEITURA", "autoleitura_cliente"),
        ]
    )
    out = ce_total_assunto_causa_view(
        frame,
        top_assuntos=2,
        top_causas_por_assunto=2,
    )
    assert not out.empty
    assert set(out["regiao"].astype(str)) == {"CE"}
    refat = out.loc[out["assunto"] == "REFATURAMENTO PRODUTOS"].sort_values("rank_causa")
    assert list(refat["causa_canonica"]) == [
        "refaturamento_corretivo",
        "consumo_elevado_revisao",
    ]


def test_motivos_taxonomia_view_builds_assunto_causa_pairs() -> None:
    def _row(ordem: str, regiao: str, assunto: str, causa: str) -> dict[str, str]:
        return {
            "ordem": ordem,
            "regiao": regiao,
            "assunto": assunto,
            "causa_canonica": causa,
        }

    frame = pd.DataFrame(
        [
            _row("1", "CE", "REFATURAMENTO PRODUTOS", "refaturamento_corretivo"),
            _row("2", "SP", "ERRO DE LEITURA", "consumo_elevado_revisao"),
            _row("3", "SP", "ERRO DE LEITURA", "consumo_elevado_revisao"),
        ]
    )
    out = motivos_taxonomia_view(frame, limit=10)
    assert not out.empty
    assert "motivo_taxonomia" in out.columns
    assert any(
        value == "ERRO DE LEITURA | consumo_elevado_revisao"
        for value in out["motivo_taxonomia"]
    )
