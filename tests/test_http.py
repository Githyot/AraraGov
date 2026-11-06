import pytest
import requests

from araragov.http import HttpClient


class SessaoQueFalha:
    def __init__(self):
        self.headers = {}
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append(url)
        raise requests.ConnectionError("sem rota")


def test_servidor_fora_do_ar_e_pulado_depois_da_primeira_falha():
    c = HttpClient(tentativas=3, espera_inicial=0)
    c.session = SessaoQueFalha()
    with pytest.raises(RuntimeError):
        c.get_json("https://exemplo.gov.br/a")
    assert len(c.session.chamadas) == 3
    with pytest.raises(RuntimeError, match="pulando"):
        c.get_json("https://exemplo.gov.br/b")
    assert len(c.session.chamadas) == 3  # nem tentou de novo
    with pytest.raises(RuntimeError):
        c.get_json("https://outro.gov.br/c")  # outro servidor ainda é tentado
    assert len(c.session.chamadas) == 6


class _Resp:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"ok": True}


class SessaoGeobloqueada:
    """Sem proxy, o servidor não responde (ou responde `status`); pelo proxy, responde 200."""

    def __init__(self, sem_proxy="conexao"):
        self.headers = {}
        self.chamadas = []
        self.sem_proxy = sem_proxy

    def get(self, url, proxies=None, **kwargs):
        self.chamadas.append((url, bool(proxies)))
        if proxies:
            return _Resp(200)
        if self.sem_proxy == "conexao":
            raise requests.ConnectionError("tempo esgotado")
        return _Resp(self.sem_proxy)


PROXY = "socks5h://u:senha@proxy.exemplo.com.br:1080"


def test_falha_de_conexao_tenta_pela_saida_brasileira_e_lembra_o_servidor():
    c = HttpClient(tentativas=3, espera_inicial=0, proxy_br=PROXY)
    c.session = SessaoGeobloqueada()
    assert c.get_json("https://portal.al.uf.gov.br/a") == {"ok": True}
    assert c.session.chamadas == [("https://portal.al.uf.gov.br/a", False), ("https://portal.al.uf.gov.br/a", True)]
    c.get_json("https://portal.al.uf.gov.br/b")  # já vai direto pelo Brasil
    assert c.session.chamadas[-1] == ("https://portal.al.uf.gov.br/b", True)


def test_403_tenta_pela_saida_brasileira():
    c = HttpClient(tentativas=3, espera_inicial=0, proxy_br=PROXY)
    c.session = SessaoGeobloqueada(sem_proxy=403)
    assert c.get_json("https://tce.uf.gov.br/x") == {"ok": True}
    assert [p for _, p in c.session.chamadas] == [False, True]


def test_429_nao_usa_a_saida_brasileira():
    c = HttpClient(tentativas=2, espera_inicial=0, proxy_br=PROXY)
    c.session = SessaoGeobloqueada(sem_proxy=429)
    with pytest.raises(RuntimeError):
        c.get_json("https://caixa.gov.br/x")
    assert [p for _, p in c.session.chamadas] == [False, False]


def test_sem_proxy_configurado_nada_muda():
    c = HttpClient(tentativas=2, espera_inicial=0, proxy_br="")
    c.session = SessaoGeobloqueada(sem_proxy=403)
    with pytest.raises(requests.HTTPError):
        c.get_json("https://tce.uf.gov.br/x")
    assert [p for _, p in c.session.chamadas] == [False]


def test_hosts_conhecidos_vao_direto_pelo_brasil():
    c = HttpClient(tentativas=2, espera_inicial=0, proxy_br=PROXY)
    c.session = SessaoGeobloqueada()
    c.get_json("https://arquivos.receitafederal.gov.br/x")
    assert c.session.chamadas == [("https://arquivos.receitafederal.gov.br/x", True)]
