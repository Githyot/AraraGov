import requests

from araragov.http import HttpClient


class _Resp:
    def __init__(self, status, partes, quebra=False):
        self.status_code, self.partes, self.quebra = status, partes, quebra

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, _):
        yield from self.partes
        if self.quebra:
            raise requests.exceptions.ChunkedEncodingError("Connection broken: IncompleteRead")


class _Sessao:
    def __init__(self):
        self.pedidos = []

    def get(self, url, stream, timeout, headers):
        self.pedidos.append(headers.get("Range"))
        if len(self.pedidos) == 1:
            return _Resp(200, [b"abc", b"def"], quebra=True)
        return _Resp(206, [b"ghi"])


def test_continua_download_de_onde_parou(tmp_path):
    c = HttpClient(tentativas=3, espera_inicial=0)
    c.session = _Sessao()
    destino = tmp_path / "x.zip"
    c.baixar_arquivo("https://exemplo/x.zip", destino)
    assert destino.read_bytes() == b"abcdefghi"
    assert c.session.pedidos == [None, "bytes=6-"]
