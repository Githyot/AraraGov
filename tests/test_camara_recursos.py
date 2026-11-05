import json
from decimal import Decimal

from sqlalchemy import select

from araragov import db
from araragov.collectors import camara_recursos as cr
from araragov.exportar import exportar

from .conftest import FIXTURES

PAGINAS = FIXTURES / "camara_paginas"


def test_le_pagina_do_deputado():
    d = cr.ler_pagina((PAGINAS / "deputado_160976.html").read_text(), 2025)
    assert d["pessoas"] == 9
    assert d["auxilio"] == "Recebeu R$ 29.771"
    assert d["imovel"] == "Não fez uso"
    assert d["viagens"] == 0
    assert d["verba_gabinete"][0] == (1, Decimal("125263.03"))
    assert len(d["verba_gabinete"]) == 12
    outro = cr.ler_pagina((PAGINAS / "deputado_62881.html").read_text(), 2025)
    assert outro["imovel"] == "Faz uso desde 20/01/2023"
    assert outro["viagens"] == 4


def test_le_salario_pago_por_mes():
    meses = cr.ler_remuneracao((PAGINAS / "remuneracao.html").read_text())
    assert meses[0] == (1, Decimal("44008.52"))
    assert meses[1] == (2, Decimal("46366.19"))  # a página mostra "46.366,191"
    assert len(meses) == 12


def test_coleta_e_exporta_recursos(client, tmp_path):
    with db.sessao() as s:
        for cod, nome in ((160976, "Deputada A"), (62881, "Deputado B"), (999, "Fora do Ar")):
            s.add(db.Politico(casa="camara", cargo="Deputado Federal", codigo=cod, nome=nome, uf="SP"))
    remuneracao = (PAGINAS / "remuneracao.html").read_bytes()
    for cod in (160976, 62881):
        url = cr.PAGINA.format(id=cod)
        client.bytes(url, (PAGINAS / f"deputado_{cod}.html").read_bytes())
        client.bytes(f"{url}/remuneracao", remuneracao)

    assert cr.coletar_recursos(client, 2025) == 2  # o 999 não responde e fica de fora
    with db.sessao() as s:
        tipos = {(b.codigo_politico, b.tipo) for b in s.execute(select(db.Beneficio)).scalars()}
    assert (160976, "auxilio_moradia") in tipos
    assert (62881, "imovel_funcional") in tipos
    assert (62881, "viagem_missao") in tipos
    assert (160976, "imovel_funcional") not in tipos

    exportar(tmp_path)
    a = json.loads((tmp_path / "v1/politicos/camara-160976.json").read_text())
    assert a["custo_gabinete"]["mensal"] == 132941.64
    assert a["custo_gabinete"]["referencia"] == "2025-12"
    assert a["custo_gabinete"]["origem"] == "verba_gabinete"
    assert a["verba_gabinete"]["anos"]["2025"]["por_mes"][0] == {"mes": 1, "valor": 125263.03}
    assert a["salario_pago"]["por_ano"][0]["ano"] == 2025
    moradia = next(b for b in a["beneficios"] if b["tipo"] == "auxilio_moradia")
    assert moradia["valor_ano"] == 29771.0
    assert "2025" in a["beneficios_anos"]
    b = json.loads((tmp_path / "v1/politicos/camara-62881.json").read_text())
    assert any(x["descricao"] == "4 viagens em missão oficial" for x in b["beneficios"])
