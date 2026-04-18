from __future__ import annotations

import pandas as pd

from src.data_plane.views import sp_causas_por_tipo_medidor_view


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
