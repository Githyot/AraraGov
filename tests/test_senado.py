import pytest
from sqlalchemy import select

from araragov import db
from araragov.collectors import senado


def test_senadores(client):
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    assert senado.coletar_senadores(client) == 2
    with db.sessao() as s:
        p = s.execute(select(db.Politico).where(db.Politico.codigo == 475)).scalar_one()
    assert (p.nome, p.partido, p.uf, p.cargo) == ("Confúcio Moura", "MDB", "RO", "Senador")


def test_votacoes_gravadas_uma_vez(client):
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    senado.coletar_senadores(client)
    client.json(f"{senado.API}/votacao", "senado_votacao.json")  # mesma resposta p/ os 2 senadores

    assert senado.coletar_votacoes(client, 2025) == 1
    with db.sessao() as s:
        v = s.get(db.Votacao, "senado:7001")
        votos = {x.codigo_politico: x.voto for x in s.execute(select(db.Voto)).scalars()}
    assert v.proposicao == "PL 10/2025"
    assert votos == {475: "sim", 5000: "ausente"}


def test_votacoes_exige_senadores(client):
    with pytest.raises(RuntimeError):
        senado.coletar_votacoes(client, 2025)


def test_despesas_ceaps(client):
    client.json(senado.CEAPS_URL.format(ano=2025), "ceaps_2025.json")
    assert senado.coletar_despesas(client, 2025) == 4
    with db.sessao() as s:
        d = s.execute(select(db.Despesa).where(db.Despesa.chave_fonte == "2263760")).scalar_one()
    assert d.codigo_politico == 475 and float(d.valor) == 6186


def test_votacao_junta_os_votos_de_cada_senador(client):
    # A API real, filtrada por senador, traz só o voto dele em cada sessão.
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    senado.coletar_senadores(client)
    for cod in (475, 5000):
        client.json(f"{senado.API}/votacao", f"senado_votacao_{cod}.json", {"codigoParlamentar": cod})

    assert senado.coletar_votacoes(client, 2025) == 1
    with db.sessao() as s:
        votos = {x.codigo_politico: x.voto for x in s.execute(select(db.Voto)).scalars()}
    assert votos == {475: "sim", 5000: "ausente"}


def test_senadores_de_legislaturas_anteriores(client):
    from araragov import db
    from sqlalchemy import select

    client.json(f"{senado.API}/senador/lista/legislatura/56/57", "senado_lista_legislatura.json")
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    assert senado.coletar_senadores_anteriores(client) == 2
    senado.coletar_senadores(client)
    with db.sessao() as s:
        situacao = {p.codigo: p.em_exercicio for p in s.execute(select(db.Politico)).scalars()}
    assert situacao[4000] is False  # saiu do Senado
    assert situacao[475] is True  # continua no mandato


def test_votacoes_por_mes_sem_filtro_de_senador(client):
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    senado.coletar_senadores(client)
    client.json(f"{senado.API}/votacao", "senado_votacao.json")

    assert senado.coletar_votacoes(client, 2025) == 1
    pedidos = [p for u, p in client.chamadas if u == f"{senado.API}/votacao"]
    assert len(pedidos) == 12 and all("codigoParlamentar" not in p for p in pedidos)
    assert pedidos[1]["dataFim"] == "2025-02-28"
