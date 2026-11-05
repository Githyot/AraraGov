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
