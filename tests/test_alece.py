from pathlib import Path

from sqlalchemy import select

from araragov import db
from araragov.collectors import alece

FIX = Path(__file__).parent / "fixtures"
VAZIO = "﻿;;;\r\nDEPUTADO;PERIODO;EMPENHO;DESCRICAO;CNPJ;CREDOR;VALOR\r\n".encode()


def test_verba_de_desempenho_alece(client, monkeypatch):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-ce", cargo="Deputado estadual", codigo=7, nome="Agenor Neto", nome_civil="Agenor Gomes de Araujo Neto", uf="CE"))
    client.bytes(alece.VERBA.format(mes=9, ano=2025), (FIX / "alece_verba_2026_09.csv").read_bytes())
    for mes in range(1, 13):
        client.bytes(alece.VERBA.format(mes=mes, ano=2025), VAZIO)
    assert alece.VERBA.format(mes=9, ano=2025).endswith("mes=09&ano=2025")
    assert alece.coletar_despesas(client, 2025) == 3
    with db.sessao() as s:
        ds = s.execute(select(db.Despesa).order_by(db.Despesa.valor)).scalars().all()
    assert [(d.codigo_politico, float(d.valor), d.mes) for d in ds] == [(7, 99.96, 9), (None, 1234.5, 9), (7, 4000.0, 9)]
    assert ds[-1].fornecedor == "TICKET SERVICOS S/A" and ds[-1].cnpj_cpf == "47866934000174"
    assert ds[1].nome_politico == "FULANO DESCONHECIDO"


CARD = """<div class="deputado_card{cls}" style="max-width: 300px"><img src="x" alt="Foto de {nome}">
<p class="deputado_card--nome s-font-1"><a href="https://www.al.ce.gov.br/deputados/{slug}">       {nome} </a></p>
<p class="deputado_card--partido s-font-1"> {partido} </p></div>"""


def test_lista_de_deputados_alece():
    pagina = "".join([
        CARD.format(cls=" ", nome="Agenor Neto", slug="agenor-neto", partido="MDB"),
        CARD.format(cls=" licenciado", nome="Guilherme Landim", slug="guilherme-landim", partido="PSB"),
        CARD.format(cls="", nome="Ant&ocirc;nio Granja", slug="antonio-granja", partido="PSB"),
    ])
    d = alece.ler_deputados(pagina)
    assert [(x["nome"], x["partido"], x["slug"]) for x in d] == [("Agenor Neto", "MDB", "agenor-neto"), ("Antônio Granja", "PSB", "antonio-granja")]
    assert d[0]["id"] == alece.ler_deputados(pagina)[0]["id"] < 900_000
    perfil = '<div><strong>Nome Completo</strong> <span>Bruno Torquato Pedrosa</span> <span class="x">'
    assert alece.ler_nome_completo(perfil) == "Bruno Torquato Pedrosa"
