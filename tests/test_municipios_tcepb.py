import io
import zipfile
from datetime import date

from araragov.municipios import md, tcepb

CAB = ("municipio;codigo_unidade_gestora;descricao_unidade_gestora;numero_empenho;data_empenho;mes;cpf_cnpj;nome_credor;"
       "valor_empenhado;valor_liquidado;valor_pago;codigo_funcao;funcao;codigo_subfuncao;subfuncao;acao;"
       "codigo_categoria_economica;codigo_natureza;codigo_modalidade_aplicacao;codigo_elemento_despesa;elemento_despesa;historico")
LINHAS = [
    "Amparo;201009;Prefeitura Municipal de Amparo;10;2025-01-02;01-Janeiro;00008086298167;FULANA DE TAL;1.114;1.114;1.114;10;Saúde;301;Atenção Básica;Manutencao;3;3;90;46;Auxílio;bolsa",
    "Amparo;201009;Prefeitura Municipal de Amparo;4;2025-01-02;01-Janeiro;00703157000183;CNM;4.292,50;4.292,50;4.292,50;4;Administração;122;Administração Geral;Gabinete;3;3;90;39;Serviços PJ;contribuicao",
    "Amparo;201009;Prefeitura Municipal de Amparo;5;2025-01-03;01-Janeiro;00703157000183;CNM;100;100;100;4;Administração;122;Administração Geral;Gabinete;4;4;90;51;Obras;Pavimentação da rua B",
    "Amparo;201009;Prefeitura Municipal de Amparo;6;2025-01-03;01-Janeiro;00703157000183;CNM;9;9;9;4;Administração;122;Administração Geral;Folha;3;1;90;11;Salários;folha",
    "Cidade Inexistente;1;X;1;2025-01-03;01-Janeiro;00703157000183;CNM;9;9;9;4;Adm;122;Adm;X;3;3;90;39;X;x",
]


def test_cnpj_valido():
    assert tcepb.cnpj_valido("00703157000183")
    assert not tcepb.cnpj_valido("00008086298167")
    assert not tcepb.cnpj_valido("00000000000000")


def _zip(tmp_path):
    caminho = tmp_path / "despesas-2025.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("despesas-2025.csv", ("﻿" + "\n".join([CAB] + LINHAS)).encode("utf-8"))
    return caminho


class FakeClient:
    def __init__(self, arquivo):
        self.arquivo = arquivo

    def baixar_arquivo(self, url, destino):
        destino.write_bytes(self.arquivo.read_bytes())


def test_gerar_paraiba(tmp_path):
    zipado = _zip(tmp_path)
    assert tcepb.gerar(FakeClient(zipado), tmp_path / "site", [2025], hoje=date(2026, 11, 5), pasta_tmp=tmp_path / "t") == 1
    texto = next((tmp_path / "site/v1/municipios/pb").glob("*/2025-pagamentos.md")).read_text(encoding="utf-8")
    assert "08086298167" not in texto and "FULANA" not in texto
    doc = md.ler(texto)
    assert doc.meta["uf"] == "PB" and "TCE-PB" in texto
    f = doc.tabelas["favorecidos"][0]
    assert f["cnpj"] == "00.703.157/0001-83" and str(f["pago"]) == "4392.5"
    assert doc.tabelas["obras"][0]["historico"] == "Pavimentação da rua B"
    resumo = {r["grupo"].split(" (")[0]: r for r in doc.tabelas["resumo"]}
    assert str(resumo["Pessoas físicas"]["pago"]) == "1114"
    assert str(resumo["Pessoal, encargos e dívida"]["pago"]) == "9"
