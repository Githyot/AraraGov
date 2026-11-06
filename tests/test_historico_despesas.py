import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from araragov import db
from araragov.collectors import assembleias, historico
from araragov.exportar import exportar


def test_despesas_da_almg_de_anos_fechados_vem_do_historico(client, tmp_path, monkeypatch):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-mg", cargo="Deputado Estadual", codigo=1, nome="Deputado A", uf="MG"))
        for ano in (2020, date.today().year):
            s.add(db.Despesa(casa="al-mg", chave_fonte=f"x{ano}", codigo_politico=1, nome_politico="Deputado A",
                             ano=ano, mes=3, categoria="Combustível", valor=Decimal("10.50"),
                             data_documento=date(ano, 3, 1)))
    exportar(tmp_path)
    publicado = json.loads((tmp_path / "v1/historico/recursos.json").read_text())
    assert [d[4] for d in publicado["despesas"]] == [2020]  # o ano em curso não vai

    db.configurar("sqlite://")
    monkeypatch.setattr(historico, "anos_carregados", set())
    client.bytes(f"https://exemplo/v1/{historico.ARQUIVO}", (tmp_path / "v1/historico/recursos.json").read_bytes())
    client.get_json = lambda u, p=None: json.loads(client.get_bytes(u, p))
    historico.carregar(client, "https://exemplo/v1")
    with db.sessao() as s:
        s.add(db.Politico(casa="al-mg", cargo="Deputado Estadual", codigo=1, nome="Deputado A", uf="MG"))
    client.chamadas.clear()
    assert assembleias.coletar_despesas_almg(client, 2020) == 0
    assert client.chamadas == []  # nenhum pedido à ALMG
    with db.sessao() as s:
        d = s.execute(select(db.Despesa)).scalar_one()
    assert (d.ano, d.valor, d.data_documento) == (2020, Decimal("10.50"), date(2020, 3, 1))
