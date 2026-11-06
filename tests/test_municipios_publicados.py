import json
from datetime import date

from araragov.municipios import md, publicados


class Falso:
    def __init__(self, arquivos):
        self.arquivos = arquivos
        self.pedidos = []

    def get_bytes(self, url, params=None):
        self.pedidos.append(url)
        if url not in self.arquivos:
            raise RuntimeError("404")
        return self.arquivos[url].encode()


TEXTO = md.escrever({"tipo": "pagamentos-municipio"}, {}, titulo="Teste")


def test_ano_fechado():
    assert publicados.ano_fechado(2024, date(2026, 1, 10))
    assert not publicados.ano_fechado(2025, date(2026, 3, 31))
    assert publicados.ano_fechado(2025, date(2026, 4, 1))
    assert not publicados.ano_fechado(2026, date(2026, 11, 6))


def test_desligado_sem_variavel(tmp_path, monkeypatch):
    monkeypatch.delenv("ARARAGOV_REAPROVEITAR", raising=False)
    c = Falso({})
    assert publicados.ano_ja_publicado(c, tmp_path, "PB", 2020, date(2026, 11, 6), "{ano}-pagamentos.md") == 0
    assert c.pedidos == []


def test_copia_publicados(tmp_path, monkeypatch):
    monkeypatch.setenv("ARARAGOV_REAPROVEITAR", "1")
    url = f"{publicados.PUBLICADO}/v1/municipios/pb/2507507/2024-pagamentos.md"
    c = Falso({url: TEXTO})
    n = publicados.ano_ja_publicado(c, tmp_path, "PB", 2024, date(2026, 11, 6), "{ano}-pagamentos.md")
    assert n == 1
    assert (tmp_path / "v1/municipios/pb/2507507/2024-pagamentos.md").read_text() == TEXTO
    assert len(c.pedidos) == 223  # um pedido por município da PB


def test_ano_aberto_nao_consulta(tmp_path, monkeypatch):
    monkeypatch.setenv("ARARAGOV_REAPROVEITAR", "1")
    c = Falso({})
    assert publicados.ano_ja_publicado(c, tmp_path, "PB", 2026, date(2026, 11, 6), "{ano}-pagamentos.md") == 0
    assert c.pedidos == []


class Resp:
    def __init__(self, headers):
        self.headers = headers
        self.ok = True


class Sessao:
    def __init__(self, headers):
        self.headers = headers

    def head(self, url, **kw):
        return Resp(self.headers)


def test_sem_mudanca_reaproveita(tmp_path, monkeypatch):
    monkeypatch.setenv("ARARAGOV_REAPROVEITAR", "1")
    bruto = "https://exemplo/despesas-2026.zip"
    sig = {"ETag": '"abc"', "Content-Length": "10"}
    md_url = f"{publicados.PUBLICADO}/v1/municipios/pb/2507507/2026-pagamentos.md"
    c = Falso({f"{publicados.PUBLICADO}/{publicados._arquivo(bruto)}": json.dumps({"url": bruto, "assinatura": sig}),
               md_url: TEXTO})
    c.session = Sessao(sig)
    n, atual = publicados.sem_mudanca(c, tmp_path, "PB", bruto, "2026-pagamentos.md")
    assert n == 1 and atual == sig
    assert bruto in (tmp_path / publicados._arquivo(bruto)).read_text()


def test_mudou_baixa_de_novo(tmp_path, monkeypatch):
    monkeypatch.setenv("ARARAGOV_REAPROVEITAR", "1")
    c = Falso({f"{publicados.PUBLICADO}/{publicados._arquivo('u')}": json.dumps({"url": "u", "assinatura": {"ETag": '"velho"'}})})
    c.session = Sessao({"ETag": '"novo"'})
    assert publicados.sem_mudanca(c, tmp_path, "PB", "u", "2026-pagamentos.md") == (0, {"ETag": '"novo"'})
    assert len(c.pedidos) == 1  # só a assinatura publicada; nenhum .md copiado
