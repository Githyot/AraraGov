from datetime import date
from decimal import Decimal as D

from araragov.municipios import emendas as em
from araragov.municipios import md

IBGE = {("BA", "SALVADOR"): (2927408, "Salvador")}


def _f(cod, mes, doc, nome, nat, tipo, valor, mun="SALVADOR"):
    return {"Código da Emenda": cod, "Ano/Mês": mes, "Código do Favorecido": doc, "Favorecido": nome,
            "Natureza Jurídica": nat, "Tipo Favorecido": tipo, "UF Favorecido": "BA", "Município Favorecido": mun,
            "Valor Recebido": valor, "Nome do Autor da Emenda": "AUTOR", "Tipo de Emenda": "Individual"}


def test_emendas_do_municipio():
    info = em.ler_emendas([{"Código da Emenda": "202500010001", "Nome do Autor da Emenda": "CONFÚCIO MOURA",
                            "Tipo de Emenda": "Emenda Individual", "Nome Função": "Cultura", "Nome Ação": "Eventos"}])
    linhas = [
        _f("202500010001", "202503", "13927801000149", "MUNICIPIO DE SALVADOR", "Município", "Pessoa Jurídica", "30000,00"),
        _f("202500010001", "202504", "13927801000149", "MUNICIPIO DE SALVADOR", "Município", "Pessoa Jurídica", "10000,00"),
        _f("202500010001", "202504", "11222333000144", "SHOWS E EVENTOS LTDA", "Sociedade Empresária Limitada", "Pessoa Jurídica", "5000,00"),
        _f("202500010001", "202504", "***.123.456-**", "FULANO", "", "Pessoa Física", "500,00"),
        _f("202500010001", "202504", "11222333000144", "OUTRA", "", "Pessoa Jurídica", "1,00", mun="FEIRA"),
        _f("202500010001", "202304", "11222333000144", "ANTIGA", "", "Pessoa Jurídica", "1,00"),
    ]
    por = em.agregar(linhas, info, IBGE, anos=[2025])
    assert list(por) == [2927408] and len(por[2927408]) == 3
    doc = md.ler(em.documento(2927408, "Salvador", "BA", por[2927408], date(2026, 11, 5)))
    r = doc.tabelas["resumo"][0]
    assert (r["valor"], r["para_prefeitura"], r["para_outros"]) == ("45500", "40000", "5500")
    rec = doc.tabelas["recebido"]
    assert rec[0]["favorecido"] == "MUNICIPIO DE SALVADOR" and rec[0]["autor"] == "CONFÚCIO MOURA"
    assert rec[1]["cnpj"] == "11.222.333/0001-44" and rec[1]["funcao"] == "Cultura"
    pf = rec[2]
    assert pf["favorecido"] == em.PESSOAS_FISICAS and pf["cnpj"] is None and "FULANO" not in str(doc.tabelas)
    assert doc.tabelas["autores"][0]["valor"] == "45500"
    assert doc.tabelas["sem-dados"][0]["esfera"] == "municipal"
