from datetime import date
from pathlib import Path

from sqlalchemy import select

from araragov import db
from araragov.collectors import assembleias as al

FIX = Path(__file__).parent / "fixtures"


def _almg(client):
    client.json(f"{al.ALMG_API}/deputados/em_exercicio", "almg_em_exercicio.json")
    client.json(f"{al.ALMG_API}/deputados/12193", "almg_deputado_12193.json")
    client.json(f"{al.ALMG_API}/deputados/28859", "almg_deputado_28859.json")


def test_deputados_almg_substituem_lista_anterior(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-mg", cargo="Deputado estadual", codigo=99, nome="Saiu"))
    _almg(client)
    assert al.coletar_deputados_almg(client) == 2
    with db.sessao() as s:
        ps = {p.codigo: p for p in s.execute(select(db.Politico).where(db.Politico.casa == "al-mg")).scalars()}
    assert set(ps) == {12193, 28859}
    assert (ps[12193].nome, ps[12193].partido, ps[12193].sexo, ps[12193].uf) == ("Adalclever Lopes", "PV", "Masculino", "MG")
    assert ps[28859].sexo == "Feminino"


def test_verbas_almg(client):
    _almg(client)
    al.coletar_deputados_almg(client)
    for mes in range(1, 13):
        for cod in (12193, 28859):
            arq = "almg_verbas.json" if (cod, mes) == (12193, 3) else "almg_vazio.json"
            client.json(f"{al.ALMG_API}/prestacao_contas/verbas_indenizatorias/deputados/{cod}/2025/{mes}", arq)
    assert al.coletar_despesas_almg(client, 2025) == 2
    with db.sessao() as s:
        ds = s.execute(select(db.Despesa).order_by(db.Despesa.valor)).scalars().all()
    assert [float(d.valor) for d in ds] == [240.84, 273.42]
    assert ds[1].data_documento == date(2025, 3, 11) and ds[1].mes == 3 and ds[1].codigo_politico == 12193
    assert ds[1].categoria == "Combustível e lubrificante"


def test_alesp(client):
    client.bytes(al.ALESP_DEPUTADOS, (FIX / "alesp_deputados.xml").read_bytes())
    client.bytes(al.ALESP_DESPESAS, (FIX / "alesp_despesas.xml").read_bytes())
    assert al.coletar_deputados_alesp(client) == 2
    # duas despesas idênticas no mesmo mês contam as duas; 2015 fica de fora
    assert al.coletar_despesas_alesp(client, 2025) == 3
    with db.sessao() as s:
        ds = s.execute(select(db.Despesa).order_by(db.Despesa.valor)).scalars().all()
        p = s.execute(select(db.Politico).where(db.Politico.codigo == 1139)).scalar_one()
    assert (p.nome, p.partido, p.em_exercicio) == ("Agente Federal Danilo Balas", "PL", True)
    assert [d.codigo_politico for d in ds] == [None, 1139, 1139]  # ex-deputado sem cadastro atual
    assert float(ds[0].valor) == 50.5


def test_lista_da_assembleia_substitui_a_do_tse(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-mg", cargo="Deputado estadual", codigo=13123, nome="Do TSE", fonte="tse"))
    _almg(client)
    al.coletar_deputados_almg(client)
    with db.sessao() as s:
        ps = s.execute(select(db.Politico).where(db.Politico.casa == "al-mg")).scalars().all()
    assert {p.codigo for p in ps} == {12193, 28859}
    assert all(p.fonte is None for p in ps)
