import io
import json
import zipfile
from pathlib import Path

import pytest

from araragov import db

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    """Responde a URLs conhecidas com arquivos de tests/fixtures."""

    def __init__(self):
        self.rotas = {}
        self.chamadas = []

    def json(self, url, arquivo, quando=None):
        self.rotas.setdefault(url, []).append((quando or {}, ("json", arquivo)))

    def bytes(self, url, conteudo):
        self.rotas.setdefault(url, []).append(({}, ("bytes", conteudo)))

    def _achar(self, url, params):
        self.chamadas.append((url, dict(params or {})))
        for filtro, resp in self.rotas.get(url, []):
            if all(str((params or {}).get(k)) == str(v) for k, v in filtro.items()):
                return resp
        raise AssertionError(f"URL inesperada: {url} {params}")

    def get_json(self, url, params=None):
        tipo, valor = self._achar(url, params)
        return json.loads((FIXTURES / valor).read_text(encoding="utf-8"))

    def get_bytes(self, url, params=None):
        tipo, valor = self._achar(url, params)
        return valor if isinstance(valor, bytes) else (FIXTURES / valor).read_bytes()


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture(autouse=True)
def banco():
    db.configurar("sqlite://")
    yield


def zip_de(caminho: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(caminho.name, caminho.read_bytes())
    return buf.getvalue()
