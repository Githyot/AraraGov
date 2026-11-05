import gzip
import io
import zipfile

from openpyxl import Workbook

from araragov.municipios import locais


def test_codigo_da_formula():
    f = '=HYPERLINK("#"&CELL("address",OFFSET(Analítico!$B$1,MATCH(104658,Analítico!$B:$B,0)-1,3)),104658)'
    assert locais.codigo_da_celula(f) == 104658
    assert locais.codigo_da_celula(92345) == 92345 and locais.codigo_da_celula(0) is None
    assert locais.codigo_da_celula("Código da Composição") is None


def test_composicoes_da_aba_csd():
    wb = Workbook()
    ws = wb.active
    ws.title = "CSD"
    for _ in range(8):
        ws.append([None])
    ws.append([None, None, None, None, "AC", None, "SP", None] + [f"U{i}" for i in range(0)] +
              [x for uf in ["AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ"] for x in (uf, None)])
    ws.append(["Grupo", "Código da\nComposição", "Descrição", "Unidade", "Custo (R$)", "%AS", "Custo (R$)", "%AS"])
    ws.append(["Pavimentação", '=HYPERLINK("#",104658)', "PISO PODOTÁTIL", "M2", 254.31, 0, 300.5, 0])
    ws.append([None, None, None, None])
    buf = io.BytesIO()
    wb.save(buf)
    linhas = list(locais.composicoes(buf.getvalue()))
    assert (104658, "PISO PODOTÁTIL", "M2", "AC", 254.31) in linhas and (104658, "PISO PODOTÁTIL", "M2", "SP", 300.5) in linhas


def test_candidatos_com_descricoes_reais(tmp_path):
    descricoes = {
        95995: "EXECUÇÃO DE PAVIMENTO COM APLICAÇÃO DE CONCRETO ASFÁLTICO, CAMADA DE ROLAMENTO - EXCLUSIVE CARGA E TRANSPORTE. AF_11/2019",
        92811: "ASSENTAMENTO DE TUBO DE CONCRETO PARA REDES COLETORAS DE ÁGUAS PLUVIAIS, DIÂMETRO DE 600 MM, JUNTA RÍGIDA, INSTALADO EM LOCAL COM BAIXO NÍVEL DE INTERFERÊNCIAS (NÃO INCLUI FORNECIMENTO). AF_12/2015",
        101658: "LUMINÁRIA DE LED PARA ILUMINAÇÃO PÚBLICA, DE 138 W ATÉ 180 W - FORNECIMENTO E INSTALAÇÃO. AF_02/2025_PS",
        100604: "ASSENTAMENTO DE POSTE DE CONCRETO COM COMPRIMENTO NOMINAL DE 10 M, CARGA NOMINAL DE 300 DAN (NÃO INCLUI FORNECIMENTO). AF_11/2019",
        97599: "LUMINÁRIA DE EMERGÊNCIA, COM 30 LÂMPADAS LED DE 2 W, SEM REATOR - FORNECIMENTO E INSTALAÇÃO. AF_09/2024",
        101501: "ENTRADA DE ENERGIA ELÉTRICA, AÉREA, BIFÁSICA, COM CAIXA DE EMBUTIR (NÃO INCLUSO O POSTE DE CONCRETO). AF_07/2020_PS",
    }
    arq = tmp_path / "2025-09.csv.gz"
    with gzip.open(arq, "wt", encoding="utf-8", newline="") as f:
        f.write("codigo;descricao;unidade;uf;custo\n")
        for codigo, descricao in descricoes.items():
            f.write(f"{codigo};{descricao};UN;SP;10.00\n")
    destino = locais.candidatos_sinapi(arq, tmp_path / "candidatos.csv")
    achados = {l.split(";")[0]: l.split(";")[1] for l in destino.read_text(encoding="utf-8").splitlines()[1:]}
    assert achados == {"pavimentacao-cbuq": "95995", "drenagem-tubo-600": "92811",
                       "luminaria-led": "101658", "poste-concreto": "100604"}


def test_filtrar_socios(tmp_path):
    texto = ('"10448277";"2";"LUCIENE FERNANDES NOGUEIRA";"***428156**";"22";"20081103";"";"***000000**";"";"00";"5"\n'
             '"99999999";"2";"OUTRA PESSOA";"***111111**";"22";"20081103";"";"***000000**";"";"00";"5"\n')
    arq = tmp_path / "Socios0.zip"
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("K3241.SOCIOCSV", texto.encode("latin-1"))
    linhas = list(locais.filtrar_socios(locais.linhas_socios(arq), {"10448277"}))
    assert linhas == [["10448277", "PF", "LUCIENE FERNANDES NOGUEIRA", "***428156**", "22", "2008-11-03", "5"]]


def test_observacoes_locais_soma_e_converte(tmp_path):
    import csv as _csv
    from decimal import Decimal

    from araragov.municipios import sinapi
    from araragov.municipios.custos import Item

    pasta = tmp_path / "sinapi"
    pasta.mkdir()
    with gzip.open(pasta / "2025-09.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = _csv.writer(f, delimiter=";")
        w.writerow(["codigo", "descricao", "unidade", "uf", "custo"])
        w.writerow(["95995", "CBUQ", "M3", "SP", "1473.95"])
        w.writerow(["96001", "FRESAGEM", "M2", "SP", "7.41"])
        w.writerow(["95995", "CBUQ", "M3", "CE", "1300"])
    itens = {"recape": Item("recape", "Recape", "m²", "pavimentacao", ("96001+95995*0.04",)),
             "cbuq": Item("cbuq", "CBUQ", "m²", "pavimentacao", ("95995*0.05",))}
    obs = {(o.item, o.uf): o for o in sinapi.observacoes_locais(itens, pasta)}
    assert obs[("cbuq", "SP")].valor == Decimal("73.70")
    assert obs[("recape", "SP")].valor == Decimal("66.37")
    assert ("recape", "CE") not in obs and obs[("cbuq", "CE")].valor == Decimal("65.00")
