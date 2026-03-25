from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(reason="Integrações reais dependem da stack Docker e serviços externos.")


def test_placeholder() -> None:
    assert True
