import io
import zipfile
from datetime import date
from pathlib import Path

from sqlalchemy import select

from araragov import db
from araragov.collectors import alba
from araragov.collectors._comum import data_excel, ler_xlsx

FIX = Path(__file__).parent / "fixtures"


def test_ler_xlsx_com_texto_em_linha():
    planilha = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        '<row r="1"><c r="B1" t="inlineStr"><is><t>DEPUTADO</t></is></c><c r="D1"><v>45962</v></c></row>'
        "</sheetData></worksheet>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", planilha)
    assert ler_xlsx(buf.getvalue()) == [[None, "DEPUTADO", None, 45962.0]]
    assert data_excel(45962.0) == date(2025, 11, 1)


def test_verbas_alba(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-ba", cargo="Deputado estadual", codigo=1, nome="Olívia Santana", nome_civil="Olivia Santana Silva", uf="BA"))
        s.add(db.Politico(casa="al-ba", cargo="Deputado estadual", codigo=2, nome="Alex da Piatã", nome_civil="Alex Santos", uf="BA"))
    client.bytes(alba.PLANILHA.format(ano=2025), (FIX / "alba_verbas_2025.xlsx").read_bytes())
    assert alba.coletar_despesas(client, 2025) == 3
    with db.sessao() as s:
        ds = s.execute(select(db.Despesa).order_by(db.Despesa.valor)).scalars().all()
    assert [(d.codigo_politico, float(d.valor), d.mes) for d in ds] == [(None, 1234.56, 2), (1, 4500.0, 11), (2, 9700.0, 1)]
    assert ds[0].categoria == "Divulgação da atividade parlamentar"
    assert ds[1].data_documento == date(2025, 11, 1)


LISTA_ALBA = """<select><option value="">Selecione</option>
<option value="/deputados/deputado-legislatura-atual/921263"> <span>Alex da Piatã</span> </option></select>
<a href="/deputados/deputado/932999"><div class="nome">Marcelino Galo</div></a>
<a href="/deputados/deputados-estaduais">EM EXERCÍCIO</a>"""
PERFIL_ALBA = '<p><strong>Nome: </strong><span>MARCELINO GALO LOPES</span></p>'


def test_lista_oficial_da_alba(client, monkeypatch):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-ba", cargo="Deputado estadual", codigo=2, nome="Alex da Piatã", nome_civil="Alex Santos", uf="BA", fonte="tse"))
        s.add(db.Politico(casa="al-ba", cargo="Deputado estadual", codigo=3, nome="Saiu", nome_civil="Fulano Saiu", uf="BA", fonte="tse"))
    lista = alba.ler_lista(LISTA_ALBA)
    assert [(o["id"], o["nome"]) for o in lista] == [(921263, "Alex da Piatã"), (932999, "Marcelino Galo")]
    assert alba.ler_nome_civil(PERFIL_ALBA) == "MARCELINO GALO LOPES"
    client.bytes(alba.LISTA, LISTA_ALBA.encode())
    client.bytes(alba.SITE + "/deputados/deputado-legislatura-atual/921263", b"<p></p>")
    client.bytes(alba.SITE + "/deputados/deputado/932999", PERFIL_ALBA.encode())
    monkeypatch.setattr(alba, "ler_lista", lambda html, f=alba.ler_lista: f(html) * 20)
    assert alba.coletar_deputados(client) == 2
    with db.sessao() as s:
        ps = {p.codigo: p for p in s.execute(select(db.Politico).where(db.Politico.casa == "al-ba")).scalars()}
    assert ps[2].em_exercicio and not ps[3].em_exercicio
    sup = ps[1_000_000 + 932999]
    assert (sup.nome, sup.nome_civil) == ("Marcelino Galo", "Marcelino Galo Lopes")
