import io
import zipfile
from decimal import Decimal

from sqlalchemy import select

from araragov import db
from araragov.collectors import emendas

CAB_E = ('"Código da Emenda";"Ano da Emenda";"Tipo de Emenda";"Código do Autor da Emenda";"Nome do Autor da Emenda";'
         '"Número da emenda";"Localidade de aplicação do recurso";"Código Município IBGE";"Município";"Código UF IBGE";"UF";'
         '"Região";"Código Função";"Nome Função";"Código Subfunção";"Nome Subfunção";"Código Programa";"Nome Programa";'
         '"Código Ação";"Nome Ação";"Código Plano Orçamentário";"Nome Plano Orçamentário";"Valor Empenhado";"Valor Liquidado";'
         '"Valor Pago";"Valor Restos A Pagar Inscritos";"Valor Restos A Pagar Cancelados";"Valor Restos A Pagar Pagos"')


def _linha(cod, ano, tipo, autor, local, funcao, emp, pago):
    campos = [cod, ano, tipo, "1", autor, "1", local, "", "", "", "BAHIA", "", "", funcao, "", "", "", "", "", "AÇÃO X",
              "", "", emp, "0,00", pago, "0,00", "0,00", "0,00"]
    return ";".join(f'"{c}"' for c in campos)


def _zip():
    e = "\n".join([
        CAB_E,
        _linha("202500010001", "2025", "Emenda Individual", "CONFÚCIO MOURA", "SALVADOR - BA", "Saúde", "100000,00", "40000,00"),
        _linha("202500010001", "2025", "Emenda Individual", "CONFÚCIO MOURA", "FEIRA - BA", "Saúde", "50000,00", "10000,00"),
        _linha("202571280004", "2025", "Emenda de Bancada", "BANCADA DA BAHIA", "BAHIA (UF)", "Educação", "9,00", "0,00"),
        _linha("202400010009", "2024", "Emenda Individual", "CONFUCIO MOURA", "X", "Saúde", "1,00", "1,00"),
    ])
    f = "\n".join([
        '"Código da Emenda";"Código do Autor da Emenda";"Nome do Autor da Emenda";"Número da emenda";"Tipo de Emenda";"Ano/Mês";'
        '"Código do Favorecido";"Favorecido";"Natureza Jurídica";"Tipo Favorecido";"UF Favorecido";"Município Favorecido";"Valor Recebido"',
        '"202500010001";"1";"CONFÚCIO MOURA";"1";"Individual";"202503";"13927801000149";"MUNICIPIO DE SALVADOR";"Município";"Pessoa Jurídica";"BA";"SALVADOR";"30000,00"',
        '"202500010001";"1";"CONFÚCIO MOURA";"1";"Individual";"202504";"13927801000149";"MUNICIPIO DE SALVADOR";"Município";"Pessoa Jurídica";"BA";"SALVADOR";"10000,00"',
        '"202500010001";"1";"CONFÚCIO MOURA";"1";"Individual";"202504";"***.123.456-**";"FULANO";"";"Pessoa Física";"BA";"SALVADOR";"500,00"',
    ])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(emendas.ARQ_EMENDAS, e.encode("latin-1"))
        z.writestr(emendas.ARQ_FAVORECIDOS, f.encode("latin-1"))
    return buf.getvalue()


def test_emendas_e_favorecidos(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="senado", cargo="Senador", codigo=475, nome="Confúcio Moura"))
    client.bytes(emendas.EMENDAS_URL, _zip())
    assert emendas.coletar_emendas(client, 2025) == 2
    with db.sessao() as s:
        es = {e.codigo: e for e in s.execute(select(db.Emenda)).scalars()}
        fs = {f.nome: f for f in s.execute(select(db.Favorecido)).scalars()}
    e = es["202500010001"]
    assert (e.casa, e.codigo_politico, e.empenhado, e.pago) == ("senado", 475, Decimal("150000.00"), Decimal("50000.00"))
    assert es["202571280004"].codigo_politico is None  # bancada não tem autor único
    assert fs["MUNICIPIO DE SALVADOR"].valor == Decimal("40000.00")
    pf = fs["Pessoas físicas (somadas)"]
    assert pf.documento is None and pf.municipio is None and pf.valor == Decimal("500.00")


def test_exporta_emendas(client, tmp_path):
    import json

    from araragov.exportar import exportar

    with db.sessao() as s:
        s.add(db.Politico(casa="senado", cargo="Senador", codigo=475, nome="Confúcio Moura"))
    client.bytes(emendas.EMENDAS_URL, _zip())
    emendas.coletar_emendas(client, 2025)
    exportar(tmp_path)
    e = json.loads((tmp_path / "v1/politicos/senado-475.json").read_text())["emendas"]
    assert (e["total_empenhado"], e["total_pago"], e["quantidade"]) == (150000.0, 50000.0, 1)
    assert e["por_area"][0] == {"nome": "Saúde", "valor": 150000.0}
    assert e["favorecidos"][0]["nome"] == "MUNICIPIO DE SALVADOR"
    assert e["anos"]["2025"]["total_pago"] == 50000.0
