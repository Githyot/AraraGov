import json

import pytest
from sqlalchemy import select

from araragov import db
from araragov.collectors import alero


def _servidores(extra=0):
    base = [
        {"nome": "Abel Rodrigues de Oliveira", "dsccargo": "Assessor Parlamentar", "dsclotacao": "GAB. DEP. JEAN OLIVEIRA"},
        {"nome": "Ada Maisa Stefani", "dsccargo": "Assessor Parlamentar", "dsclotacao": "GAB. DEP. Alex Redano"},
        {"nome": "Fulano", "dsccargo": "Assessor", "dsclotacao": "PRESIDENCIA"},
    ]
    return base + [{"nome": f"P{i}", "dsccargo": "Assessor", "dsclotacao": f"GAB. DEP. OUTRO {i}"} for i in range(extra)]


def test_agrupar_por_gabinete():
    g = alero.agrupar(_servidores())
    assert sorted(g) == ["Alex Redano", "JEAN OLIVEIRA"]


def test_equipe_dos_gabinetes_alero(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-ro", cargo="Deputado estadual", codigo=5, nome="Jean Oliveira", nome_civil="Jean Carlos de Oliveira", uf="RO"))
    client.bytes(alero.SERVIDORES, json.dumps(_servidores()).encode())
    with pytest.raises(RuntimeError):
        alero.coletar_gabinetes(client)
    client.rotas.clear()
    client.bytes(alero.SERVIDORES, json.dumps(_servidores(20)).encode())
    assert alero.coletar_gabinetes(client) == 1
    with db.sessao() as s:
        a = s.execute(select(db.Assessor)).scalar_one()
    assert (a.codigo_politico, a.nome, a.cargo, a.lotacao) == (5, "Abel Rodrigues de Oliveira", "Assessor Parlamentar", "GAB. DEP. JEAN OLIVEIRA")
