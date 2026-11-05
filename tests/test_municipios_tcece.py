from datetime import date

from araragov.municipios import md, tcece

EMP = {"codigo_orgao": "29", "codigo_unidade_orcamentaria": "01  ", "data_emissao_empenho": "2025-03-31T00:00:00",
       "numero_empenho": "31030064", "codigo_funcao": "15", "codigo_subfuncao": "451",
       "codigo_elemento_despesa": "44905100", "numero_documento_negociante": "06738793000127",
       "nome_negociante": "OBRAS EXEMPLO LTDA", "descricao_historico_empenho": "PAVIMENTACAO DA RUA A"}
PF = dict(EMP, numero_empenho="1", codigo_elemento_despesa="33903600",
          numero_documento_negociante="aLrHXtAy4Khrw+rhtcmWzw==", nome_negociante="FULANO")
FOLHA = dict(EMP, numero_empenho="2", codigo_elemento_despesa="31901100", nome_negociante="FOLHA DE PAGAMENTO")


def _pag(e, valor, estornado=0):
    return {k: e[k] for k in ("codigo_orgao", "codigo_unidade_orcamentaria", "data_emissao_empenho", "numero_empenho")} | {
        "valor_nota_pagamento": valor, "estado_de_estornado": estornado}


def test_agrega_pagamentos_pelo_empenho():
    m = tcece.agregar("Crato", [EMP, PF, FOLHA], [
        _pag(EMP, 1000.5), _pag(EMP, 500), _pag(EMP, 999, estornado=1), _pag(PF, 300), _pag(FOLHA, 72000),
        _pag(dict(EMP, numero_empenho="nao-existe"), 10),
    ])
    f = m.favorecidos["06738793000127"]
    assert str(f.pago) == "1500.5" and f.pagamentos == 2
    assert f.areas == {"Urbanismo"}
    assert m.pf_pago == 300 and len(m.pf_pessoas) == 1
    assert m.fora_pago == 72000
    assert list(m.obras.values())[0]["historico"] == "PAVIMENTACAO DA RUA A"


class FakeClient:
    def __init__(self):
        self.pedidos = []

    def get_json(self, url, params=None):
        self.pedidos.append((url, dict(params or {})))
        if url.endswith("/municipios"):
            return {"elements": [{"codigo_municipio": "001", "nome_municipio": "T.C.M.", "codigo_municipio_ibge": None},
                                 {"codigo_municipio": "049", "nome_municipio": "CRATO", "codigo_municipio_ibge": "2304202"}]}
        if params.get("data_referencia_doc") != 202501:
            return {"elements": []}
        if url.endswith("/notas_empenhos"):
            return {"elements": [EMP]}
        return {"elements": [_pag(EMP, 1000)]}


def test_gerar_grava_md_do_ceara(tmp_path):
    c = FakeClient()
    assert tcece.gerar(c, tmp_path, [2025], hoje=date(2026, 11, 5), meses=2) == 1
    doc = md.ler((tmp_path / "v1/municipios/ce/2304202/2025-pagamentos.md").read_text(encoding="utf-8"))
    assert doc.meta["uf"] == "CE" and doc.meta["municipio"] == "Crato"
    assert doc.tabelas["favorecidos"][0]["cnpj"] == "06.738.793/0001-27"
    assert "TCE-CE" in (tmp_path / "v1/municipios/ce/2304202/2025-pagamentos.md").read_text(encoding="utf-8")
    p = [q for u, q in c.pedidos if u.endswith("notas_empenhos")]
    assert p[0]["exercicio_orcamento"] == 202500 and p[0]["$count"] == 1000 and len(p) == 2
