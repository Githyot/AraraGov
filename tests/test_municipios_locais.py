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
    ws.append(["Grupo", "Código da Composição", "Descrição", "Unidade", "Custo (R$)", "%AS", "Custo (R$)", "%AS"])
    ws.append(["Pavimentação", '=HYPERLINK("#",104658)', "PISO PODOTÁTIL", "M2", 254.31, 0, 300.5, 0])
    ws.append([None, None, None, None])
    buf = io.BytesIO()
    wb.save(buf)
    linhas = list(locais.composicoes(buf.getvalue()))
    assert (104658, "PISO PODOTÁTIL", "M2", "AC", 254.31) in linhas and (104658, "PISO PODOTÁTIL", "M2", "SP", 300.5) in linhas


def test_filtrar_socios(tmp_path):
    texto = ('"10448277";"2";"LUCIENE FERNANDES NOGUEIRA";"***428156**";"22";"20081103";"";"***000000**";"";"00";"5"\n'
             '"99999999";"2";"OUTRA PESSOA";"***111111**";"22";"20081103";"";"***000000**";"";"00";"5"\n')
    arq = tmp_path / "Socios0.zip"
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("K3241.SOCIOCSV", texto.encode("latin-1"))
    linhas = list(locais.filtrar_socios(locais.linhas_socios(arq), {"10448277"}))
    assert linhas == [["10448277", "PF", "LUCIENE FERNANDES NOGUEIRA", "***428156**", "22", "2008-11-03", "5"]]
