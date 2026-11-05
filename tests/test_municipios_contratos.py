import csv
import io
import zipfile
from datetime import date
from decimal import Decimal as D

from araragov.municipios import contratos, md

CAB = ["Município", "Entidade", "Código da Licitação", "Código do Ajuste", "Modalidade de licitação",
       "Número do processo licitatório", "Ano do processo licitatório", "Objeto da licitação",
       "Descrição do objeto da licitação", "Valor da declaração", "Fundamento Legal - dispensa de licitação",
       "Instrumento", "Nº do contrato", "Ano do contrato", "Valor total do contrato", "Descrição do objeto contratado",
       "Quantidade do objeto contratado", "Unidade do objeto contratado", "Nota de Empenho/Documento Similar",
       "Data da Nota de Empenho/Documento Similar", "Valor da Nota de Empenho/Documento Similar",
       "CNPJ da empresa contratada", "Nome da empresa contratada", "Vigência do contrato - Data início",
       "Vigência do contrato - Data Término", "Vigência do contrato - Data Assinatura", "Modo de fornecimento"]


def _l(cod, modalidade, objeto, total, qtd, unid, cnpj, empresa, fund=""):
    return ["Adamantina", "PREFEITURA MUNICIPAL DE ADAMANTINA", "1", cod, modalidade, "", "", "Obras", objeto, "",
            fund, "Contrato", f"C{cod}", "2024", total, objeto, qtd, unid, "", "", "", cnpj, empresa, "", "", "01/07/2024", ""]


LINHAS = [
    _l("1", "Concorrencia", "PAVIMENTAÇÃO ASFÁLTICA EM CBUQ DA RUA A", "300000,0", "1000,0", "M2", "11.222.333/0001-81", "ASFALTO SA"),
    _l("1", "Concorrencia", "PAVIMENTAÇÃO ASFÁLTICA EM CBUQ DA RUA A", "300000,0", "1000,0", "M2", "11.222.333/0001-81", "ASFALTO SA"),
    _l("2", "Pregao Eletronico", "AQUISIÇÃO DE LUMINÁRIAS LED PARA ILUMINAÇÃO PÚBLICA", "50000,0", "3,0", "ITENS", "22.333.444/0001-55", "LUZ LTDA"),
    _l("3", "Contratacao Direta - Dispensa de licitacao", "SERVIÇO DE BUFFET", "40000,0", "1,0", "UN", "33.444.555/0001-66", "FESTA LTDA", "Art. 75, II"),
    _l("4", "Contratacao Direta - Dispensa de licitacao", "SERVIÇO DE SOM", "45000,0", "1,0", "UN", "33.444.555/0001-66", "FESTA LTDA", "Art. 75, II"),
    _l("5", "Contratacao Direta - Inexigibilidade de licitacao", "SHOW", "90000,0", "1,0", "UN", "33.444.555/0001-66", "FESTA LTDA", "Art. 74"),
]


def test_classificar_e_unidade():
    assert contratos.classificar("Recapeamento asfáltico da Av. Brasil") == "recape-cbuq"
    assert contratos.classificar("Operação tapa-buraco com CBUQ") is None
    assert contratos.classificar("Construção de creche Proinfância tipo 1") == "creche"
    assert contratos.classificar("Aquisição de gêneros alimentícios para creche") is None
    assert contratos.unidade("m²") == "m²" and contratos.unidade("ITENS") is None
    assert contratos.classificar("CONSTRUÇÃO UNIDADE ESCOLAR") == "escola"
    assert contratos.classificar("Serviços de pintura do prédio onde será a nova Creche") is None
    assert contratos.classificar("Substituição de vidro nas unidades básicas de saúde (UBS)") is None


def test_quantidade_incoerente_nao_compara():
    refs = {("escola", 2024): {"minimo": "1661.31", "maximo": "2030.49", "nivel": "1", "avisos": None}}
    r = contratos.comparar("escola", "m²", D("1"), D("13382986.70"), refs, 2024, {"escola": "m²"})
    assert r["comparacao"].startswith("Quantidade ou unidade incoerente") and r["ref_maximo"] is None


def test_agregar_compara_e_aponta_diretas(tmp_path):
    refs = {("pavimentacao-cbuq", 2024): {"minimo": "60.00", "maximo": "100.00", "nivel": "3", "avisos": None}}
    unid = {"pavimentacao-cbuq": "m²", "luminaria-led": "un"}
    por = contratos.agregar([dict(zip(CAB, l)) for l in LINHAS], 2024, refs, unid)
    m = por["Adamantina"]
    assert len(m["contratos"]) == 5  # linha repetida conta uma vez
    obra = next(o for o in m["obras"] if o["item"] == "pavimentacao-cbuq")
    assert obra["valor_unitario"] == D("300.00") and obra["comparacao"] == "200.0% acima da faixa de referência"
    led = next(o for o in m["obras"] if o["item"] == "luminaria-led")
    assert led["comparacao"] == "Quantidade não informada no contrato"
    texto = contratos.documento(3500105, "Adamantina", 2024, m, date(2026, 11, 5))
    doc = md.ler(texto)
    d = doc.tabelas["contratacoes-diretas"]
    assert d[0]["cnpj"] == "33.444.555/0001-66" and d[0]["contratacoes"] == "3" and d[0]["valor"] == "175000"
    assert doc.tabelas["obras"][0]["comparacao"].endswith("acima da faixa de referência")


def test_faixa_pelos_contratos_do_estado():
    def obra(v):
        return {"item": "poste-concreto", "unidade": "un", "quantidade": D("10"), "valor": D(v) * 10,
                "valor_unitario": D(v), "comparacao": contratos.SEM_FAIXA}
    precos = ["1000", "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900", "5000"]
    por = {"A": {"obras": [obra(v) for v in precos]}, "B": {"obras": [obra("2600")]}}
    assert contratos.comparar_com_contratos(por, 2024, {"poste-concreto": "un"}) == 12
    caro = por["B"]["obras"][0]
    assert caro["nivel"] == "1" and caro["comparacao"].endswith("acima da faixa de referência")
    assert "12 contratos" in caro["aviso"]
    assert por["A"]["obras"][4]["comparacao"] == "Dentro da faixa de referência"
    assert contratos.comparar_com_contratos({"A": {"obras": [obra("1")]}}, 2024, {"poste-concreto": "un"}) == 0
