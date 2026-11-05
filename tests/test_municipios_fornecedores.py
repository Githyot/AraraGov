from datetime import date
from decimal import Decimal as D

from araragov.municipios import fornecedores as fo
from araragov.municipios import md


def _sancao(tipo, doc, cadastro="CEIS"):
    return {"CADASTRO": cadastro, "TIPO DE PESSOA": tipo, "CPF OU CNPJ DO SANCIONADO": doc,
            "NOME DO SANCIONADO": "X", "RAZÃO SOCIAL - CADASTRO RECEITA": "OBRAS BOAS LTDA",
            "CATEGORIA DA SANÇÃO": "Impedimento/proibição de contratar com prazo determinado",
            "DATA INÍCIO SANÇÃO": "20/06/2023", "DATA FINAL SANÇÃO": "20/06/2028",
            "ÓRGÃO SANCIONADOR": "Prefeitura de Outra Cidade", "UF ÓRGÃO SANCIONADOR": "MG",
            "ESFERA ÓRGÃO SANCIONADOR": "MUNICIPAL", "ABRAGÊNCIA DA SANÇÃO": "Na esfera do órgão sancionador",
            "NÚMERO DO PROCESSO": "12/2023", "FUNDAMENTAÇÃO LEGAL": "LEI 14133 - ART. 156, III"}


def test_sancoes_so_empresas():
    s = fo.ler_sancoes([_sancao("J", "11222333000144"), _sancao("F", "12345678901")])
    assert list(s) == ["11222333000144"]
    r = s["11222333000144"][0]
    assert r["cnpj"] == "11.222.333/0001-44" and r["inicio"] == "2023-06-20" and r["esfera"] == "Municipal"


def _despesa(cnpj, sq, valor_, tipo="2", nm_ue="ADAMANTINA"):
    return {"CD_TIPO_ELEICAO": tipo, "SG_UF": "SP", "SG_UE": "61018", "NM_UE": nm_ue, "SQ_CANDIDATO": sq,
            "NM_CANDIDATO": "FULANO DE TAL", "DS_CARGO": "Prefeito", "SG_PARTIDO": "ABC",
            "NR_CPF_CNPJ_FORNECEDOR": cnpj, "NM_FORNECEDOR": "GRAFICA", "NM_FORNECEDOR_RFB": "GRAFICA RAPIDA LTDA",
            "DS_ORIGEM_DESPESA": "Publicidade por materiais impressos", "VR_DESPESA_CONTRATADA": valor_}


def test_campanha_so_quem_tambem_recebeu_do_municipio():
    traduz = lambda uf, tse, nome: 3500105 if nome == "ADAMANTINA" else None  # noqa: E731
    linhas = [_despesa("55666777000188", "250001", "1000,50"), _despesa("55666777000188", "250001", "500,00"),
              _despesa("99888777000166", "250001", "300,00"),  # não recebeu da prefeitura
              _despesa("55666777000188", "250001", "900,00", tipo="1"),  # suplementar
              _despesa("12345678901", "250001", "100,00")]  # pessoa física
    por = fo.ler_campanhas(linhas, 2024, traduz, {3500105: {"55666777000188"}})
    c = por[3500105][("55666777000188", "250001")]
    assert c.valor == D("1500.50") and c.empresa == "GRAFICA RAPIDA LTDA" and len(por[3500105]) == 1


def _escrever(pasta, nome, meta, tabelas):
    (pasta / nome).write_text(md.escrever(meta, tabelas), encoding="utf-8")


def test_documento_junta_fases(tmp_path):
    p = tmp_path / "3500105"
    p.mkdir()
    _escrever(p, "2024-pagamentos.md", {"tipo": "municipio-pagamentos", "ano": 2024}, {"favorecidos": [
        {"posicao": 1, "cnpj": "11.222.333/0001-44", "favorecido": "OBRAS BOAS LTDA", "pago": D("500000")},
        {"posicao": 2, "cnpj": "55.666.777/0001-88", "favorecido": "GRAFICA RAPIDA LTDA", "pago": D("20000")},
        {"posicao": 3, "cnpj": "00.111.222/0001-33", "favorecido": "ENERGIA SA", "pago": D("900000")}]})
    _escrever(p, "2024-contratos.md", {"tipo": "municipio-contratos", "ano": 2024}, {
        "contratos": [{"contrato": "1", "cnpj": "11.222.333/0001-44", "empresa": "OBRAS BOAS LTDA",
                       "orgao": "PREFEITURA", "valor": D("800000")}],
        "obras": [{"contrato": "1", "cnpj": "11.222.333/0001-44", "empresa": "OBRAS BOAS LTDA",
                   "orgao": "PREFEITURA", "valor": D("800000")}]})
    _escrever(p, "resumo.md", {"tipo": "municipio-resumo"}, {"mandatos": [
        {"cargo": "Prefeito", "inicio": 2025, "fim": 2028, "sq_candidato": "250001"}]})
    forn = fo.fornecedores_do_municipio(p)
    assert forn["11222333000144"].contratos == 1 and forn["11222333000144"].valor_contratos == D("800000")
    sancoes = fo.ler_sancoes([_sancao("J", "11222333000144")])
    camp = fo.ler_campanhas([_despesa("55666777000188", "250001", "1000,00")], 2024,
                            lambda *a: 3500105, {3500105: set(forn)})[3500105]
    texto = fo.documento(3500105, "Adamantina", "SP", forn, sancoes, camp, fo.eleitos_do_municipio(p),
                         [2024], date(2026, 11, 5), "2026-11-04", {"00111222000133": ["FULANO 2024"]})
    doc = md.ler(texto)
    linhas = doc.tabelas["fornecedores"]
    ind = {l["empresa"]: l["indicios"] for l in linhas}
    assert ind == {"OBRAS BOAS LTDA": "Sanção no CEIS (Prefeitura de Outra Cidade, 2023-2028)",
                   "GRAFICA RAPIDA LTDA": "Fornecedora de campanha (2024)",
                   "ENERGIA SA": "Recebeu emenda federal direto (FULANO 2024)"}
    assert doc.tabelas["campanha"][0]["eleito"] == "Sim (Prefeito 2025-2028)"
    assert doc.tabelas["sancoes"][0]["cadastro"] == "CEIS"
    assert doc.tabelas["sem-dados"][0]["responsavel"] == "Receita Federal"
    assert "superfatur" not in texto.lower()


def test_plataformas_ficam_de_fora():
    def camp(ibge):
        return {("13347016000117", str(ibge)): fo.Campanha("13347016000117", "FACEBOOK", 2024, str(ibge), "X", "Prefeito", "A")}
    por = {i: camp(i) for i in range(fo.MAX_MUNICIPIOS_CAMPANHA + 1)}
    por[0][("55666777000188", "1")] = fo.Campanha("55666777000188", "GRAFICA", 2024, "1", "Y", "Prefeito", "B")
    limpo = fo.remover_plataformas(por)
    assert list(limpo[0]) == [("55666777000188", "1")] and not limpo[1]


def test_cpf_colado_ao_nome_sai():
    from araragov.municipios.tcesp import _resumir
    assert _resumir("LUCIANA MACEDO14576486870") == "LUCIANA MACEDO"
