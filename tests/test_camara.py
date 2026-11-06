from decimal import Decimal

from sqlalchemy import select

from araragov import db
from araragov.collectors import camara

from .conftest import FIXTURES, zip_de


def test_deputados_pagina_e_marca_exercicio(client):
    client.json(f"{camara.API}/legislaturas", "camara_legislaturas.json")
    url = f"{camara.API}/deputados"
    client.json(url, "camara_deputados_leg57.json", {"idLegislatura": 57, "pagina": 1})
    client.json(url, "camara_deputados_leg57_p2.json", {"idLegislatura": 57, "pagina": 2})
    client.json(url, "camara_deputados_atuais.json", {"pagina": 1})

    assert camara.coletar_deputados(client) == 3
    with db.sessao() as s:
        deps = {p.codigo: p for p in s.execute(select(db.Politico)).scalars()}
    assert deps[220593].partido == "PSOL"
    assert deps[220593].em_exercicio is True
    assert deps[204554].em_exercicio is False
    assert deps[62881].url_foto.endswith("62881.jpg")


def _rotas_votacoes(client):
    for nome in ("votacoes", "votacoesVotos", "votacoesProposicoes", "votacoesOrientacoes"):
        client.bytes(f"{camara.ARQUIVOS}/{nome}/csv/{nome}-2025.csv", (FIXTURES / f"{nome}-2025.csv").read_bytes())


def test_votacoes_so_nominais_com_orientacao(client):
    _rotas_votacoes(client)
    assert camara.coletar_votacoes(client, 2025) == 1
    with db.sessao() as s:
        v = s.get(db.Votacao, "camara:2500001-10")
        votos = s.execute(select(db.Voto).order_by(db.Voto.codigo_politico)).scalars().all()
    assert v.proposicao == "PL 1/2025"
    assert v.resultado == "Aprovada"
    assert v.orientacoes == {"PL": "Sim", "PSOL": "Não"}
    assert [x.voto for x in votos] == ["sim", "sim", "nao"]


def test_votacoes_idempotente(client):
    _rotas_votacoes(client)
    camara.coletar_votacoes(client, 2025)
    camara.coletar_votacoes(client, 2025)
    with db.sessao() as s:
        assert len(s.execute(select(db.Voto)).scalars().all()) == 3


def test_despesas_ceap(client):
    client.bytes(camara.CEAP_URL.format(ano=2025), zip_de(FIXTURES / "cota_camara_2025.csv"))
    assert camara.coletar_despesas(client, 2025) == 5
    camara.coletar_despesas(client, 2025)  # reexecutar não duplica
    with db.sessao() as s:
        despesas = s.execute(select(db.Despesa)).scalars().all()
    assert len(despesas) == 5
    lideranca = [d for d in despesas if d.codigo_politico is None]
    assert len(lideranca) == 1 and lideranca[0].valor == Decimal("1467")
    assert sum(d.valor for d in despesas if d.codigo_politico == 62881) == Decimal("3152.28")


def test_legislatura_pela_data_quando_api_falha(client):
    from datetime import date

    assert camara.legislatura_pela_data(date(2023, 2, 1)) == 57
    assert camara.legislatura_pela_data(date(2026, 12, 31)) == 57
    assert camara.legislatura_pela_data(date(2027, 1, 15)) == 57
    assert camara.legislatura_pela_data(date(2027, 2, 1)) == 58
    # sem rota cadastrada, o cliente falso levanta erro, como num 504
    assert camara.legislatura_atual(client) == camara.legislatura_pela_data()


def test_lancamento_de_outro_ano_nao_quebra_a_carga():
    from araragov import db
    from araragov.collectors._comum import substituir_despesas
    from araragov.db import Despesa

    linha = {"casa": "camara", "chave_fonte": "x1", "ano": 2019, "mes": 5, "valor": 10}
    with db.sessao() as s:
        substituir_despesas(s, "camara", 2019, [linha])
    with db.sessao() as s:  # o arquivo de 2020 traz o mesmo lançamento, datado de 2019
        assert substituir_despesas(s, "camara", 2020, [{**linha, "valor": 12}]) == 1
    with db.sessao() as s:
        assert [d.valor for d in s.query(Despesa).filter_by(chave_fonte="x1")] == [12]
