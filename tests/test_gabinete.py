from sqlalchemy import select

from araragov import db
from araragov.collectors import gabinete, senado

from .conftest import FIXTURES


def test_camara_so_lotados_em_gabinete(client):
    client.bytes(gabinete.CAMARA_URL, (FIXTURES / "funcionarios.csv").read_bytes())
    assert gabinete.coletar_camara(client) == 1
    with db.sessao() as s:
        a = s.execute(select(db.Assessor)).scalar_one()
    assert (a.codigo_politico, a.nome, a.funcao) == (62881, "ZUNARA DA SILVA", "SP20C")


def test_senado_casa_nome_do_gabinete(client):
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    senado.coletar_senadores(client)
    client.json(gabinete.SENADO_URL, "senado_servidores.json")
    assert gabinete.coletar_senado(client) == 2
    with db.sessao() as s:
        por_nome = {a.nome: a.codigo_politico for a in s.execute(select(db.Assessor)).scalars()}
    assert por_nome == {"ABI CUSTÓDIO DIVINO FILHO": 475, "FULANO": None}


def test_casar_nome_parcial():
    senadores = {"weverton": 1, "rogerio carvalho": 2, "rogerio marinho": 3}
    assert gabinete._casar("weverton rocha", senadores) == 1
    assert gabinete._casar("rogerio carvalho", senadores) == 2
    assert gabinete._casar("rogerio", senadores) is None  # ambíguo
