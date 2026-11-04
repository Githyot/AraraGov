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
