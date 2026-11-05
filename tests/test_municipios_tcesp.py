import csv
import io
import zipfile
from datetime import date
from decimal import Decimal as D

from araragov.municipios import md, tcesp

CAMPOS = ["id_despesa_detalhe", "ano_exercicio", "ds_municipio", "codigo_municipio_ibge", "ds_orgao", "mes_referencia",
          "mes_ref_extenso", "tp_despesa", "nr_empenho", "tp_identificador_despesa", "nr_identificador_despesa",
          "ds_despesa", "dt_emissao_despesa", "vl_despesa", "ds_funcao_governo", "ds_subfuncao_governo", "cd_programa",
          "ds_programa", "cd_acao", "ds_acao", "ds_fonte_recurso", "ds_cd_aplicacao_fixo", "ds_modalidade_lic",
          "ds_elemento", "historico_despesa"]


def _l(tp, empenho, tipo_id, ident, nome, v, funcao, sub, elemento, hist="", acao="Acao"):
    return ["1", "2024", "Bady Bassitt", "3504602", "PREFEITURA MUNICIPAL DE BADY BASSITT", "1", "Janeiro", tp,
            empenho, tipo_id, ident, nome, "03/01/2024", v, funcao, sub, "1", "Prog", "1", acao, "TESOURO", "0110",
            "PREGÃO", elemento, hist]


LINHAS = [
    _l("Empenhado", "1-2024", "CNPJ - PESSOA JURÍDICA", "05615940000109", "BMS CONSTRUCOES LTDA", "999999,00", "URBANISMO", "INFRA-ESTRUTURA URBANA", "44905191 - OBRAS EM ANDAMENTO"),
    _l("Valor Pago", "1-2024", "CNPJ - PESSOA JURÍDICA", "05615940000109", "BMS CONSTRUCOES LTDA", "232.745,91", "URBANISMO", "INFRA-ESTRUTURA URBANA", "44905191 - OBRAS EM ANDAMENTO", "Pavimentacao asfaltica da Rua A", "Pavimentacao"),
    _l("Valor Pago", "1-2024", "CNPJ - PESSOA JURÍDICA", "05615940000109", "BMS CONSTRUCOES LTDA", "1.000,00", "URBANISMO", "INFRA-ESTRUTURA URBANA", "44905191 - OBRAS EM ANDAMENTO", "Pavimentacao asfaltica da Rua A", "Pavimentacao"),
    _l("Valor Pago", "7-2024", "CNPJ - PESSOA JURÍDICA", "11222333000181", "MARIA SOUZA 98765432100", "50.000,00", "EDUCAÇÃO", "ALIMENTAÇÃO E NUTRIÇÃO", "33903007 - GENEROS DE ALIMENTACAO"),
    _l("Valor Pago", "8-2024", "CPF - PESSOA FÍSICA", "12345678901", "FULANO DE TAL", "800,00", "SAÚDE", "ATENÇÃO BÁSICA", "33903600 - OUTROS SERVICOS PF"),
    _l("Valor Pago", "9-2024", "CNPJ - PESSOA JURÍDICA", "51857878000189", "FOLHA DE PAGAMENTO", "90.000,00", "ADMINISTRAÇÃO", "ADMINISTRAÇÃO GERAL", "31901101 - VENCIMENTOS"),
]


def _zip(tmp_path):
    s = io.StringIO()
    w = csv.writer(s, delimiter=";")
    w.writerow(CAMPOS)
    w.writerows(LINHAS)
    caminho = tmp_path / "d.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("despesas-2024.csv", s.getvalue().encode("latin-1"))
    return caminho


class Cliente:
    def __init__(self, arquivo):
        self.arquivo = arquivo

    def baixar_arquivo(self, url, destino):
        assert url == tcesp.DESPESAS_URL.format(ano=2024)
        destino.write_bytes(self.arquivo.read_bytes())


def test_agregar_e_documento(tmp_path):
    ms = tcesp.agregar(tcesp.linhas_despesas(_zip(tmp_path)))
    m = ms[3504602]
    assert set(m.favorecidos) == {"05615940000109", "11222333000181"}
    assert m.favorecidos["05615940000109"].pago == D("233745.91")
    assert m.pf_pago == D("800.00") and len(m.pf_pessoas) == 1
    assert m.fora_pago == D("90000.00")
    assert list(m.obras.values())[0]["pago"] == D("233745.91")

    saida = tmp_path / "site"
    resumo = saida / "v1/municipios/sp/3504602/resumo.md"
    resumo.parent.mkdir(parents=True)
    resumo.write_text(md.escrever({"tipo": "municipio-resumo"}, {"mandatos": [
        {"eleicao": 2020, "inicio": 2021, "fim": 2024, "cargo": "Prefeito", "nome": "Ana", "partido": "PX"}]}), encoding="utf-8")
    assert tcesp.gerar(Cliente(_zip(tmp_path)), saida, [2024], hoje=date(2026, 11, 5)) == 1
    texto = (saida / "v1/municipios/sp/3504602/2024-pagamentos.md").read_text(encoding="utf-8")
    assert "12345678901" not in texto and "FULANO" not in texto
    assert "98765432100" not in texto and "MARIA SOUZA" in texto  # MEI: nome fica, CPF sai
    doc = md.ler(texto)
    assert doc.meta["governo"] == "Ana (PX), mandato 2021-2024"
    fav = doc.tabelas["favorecidos"]
    assert fav[0]["cnpj"] == "05.615.940/0001-09" and fav[0]["pago"] == "233745.91"
    assert doc.tabelas["obras"][0]["historico"] == "Pavimentacao asfaltica da Rua A"
    assert {(r["funcao"], r["posicao"]) for r in doc.tabelas["areas-favorecidos"]} == {("Urbanismo", "1"), ("Educação", "1")}


def test_valor():
    assert tcesp.valor("1.234,56") == D("1234.56") and tcesp.valor("") == 0 and tcesp.valor("x") == 0
