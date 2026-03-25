"""Master data Bronze ingestors."""

from __future__ import annotations

from src.ingestion.snapshot_ingestor import SnapshotIngestor


class CadastroDistribuidorasIngestor(SnapshotIngestor):
    pass


class CadastroUTsIngestor(SnapshotIngestor):
    pass


class CadastroCOsIngestor(SnapshotIngestor):
    pass


class CadastroBasesIngestor(SnapshotIngestor):
    pass


class CadastroUCsIngestor(SnapshotIngestor):
    pass


class CadastroInstalacoesIngestor(SnapshotIngestor):
    pass


class CadastroColaboradoresIngestor(SnapshotIngestor):
    pass


CADASTRO_INGESTORS = {
    "cadastro_distribuidoras": CadastroDistribuidorasIngestor,
    "cadastro_uts": CadastroUTsIngestor,
    "cadastro_cos": CadastroCOsIngestor,
    "cadastro_bases": CadastroBasesIngestor,
    "cadastro_ucs": CadastroUCsIngestor,
    "cadastro_instalacoes": CadastroInstalacoesIngestor,
    "cadastro_colaboradores": CadastroColaboradoresIngestor,
}
