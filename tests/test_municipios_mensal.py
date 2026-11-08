from datetime import date
from decimal import Decimal

from araragov.municipios import md, mensal
from araragov.municipios.financas import SICONFI, Ente


def _i(conta, valor, nat="C", receita=None, funcao=None):
    return {"conta_contabil": conta, "valor": valor, "natureza_conta": nat,
            "natureza_receita": receita, "funcao": funcao}


ITENS = [
    _i("621200000", 1000, receita="11125001"),          # IPTU
    _i("621200000", 50, "D", receita="11125001"),       # estorno
    _i("621200000", 3000, receita="17115111"),          # FPM
    _i("621310100", 600, "D", receita="17115111"),      # dedução para o Fundeb
    _i("621200000", 200, receita="13210011"),           # rendimentos
    _i("621100000", 9999, "D", receita="11125001"),     # a realizar: ignorado
    _i("622130400", 700, funcao="10"),
    _i("622130400", 20, "D", funcao="10"),
    _i("622130400", 300, funcao="12"),
    _i("622130100", 5000, funcao="10"),                 # empenhado a liquidar: ignorado
]


def test_resumo_mes():
    totais, funcoes = mensal.resumo_mes(ITENS)
    assert totais["impostos"] == Decimal(950)
    assert totais["repasses"] == Decimal(2400)
    assert totais["outras"] == Decimal(200)
    assert totais["arrecadado"] == Decimal(3550)
    assert totais["gasto"] == Decimal(980)
    assert funcoes == {"10": Decimal(680), "12": Decimal(300)}
    assert mensal.resumo_mes([]) is None


def test_meses_possiveis_e_abertos():
    hoje = date(2026, 11, 8)
    assert mensal.meses_possiveis(2025, hoje) == list(range(1, 13))
    assert mensal.meses_possiveis(2026, hoje) == list(range(1, 11))
    assert mensal.aberto(2026, 9, hoje) and not mensal.aberto(2026, 7, hoje)


class Cliente:
    def __init__(self):
        self.pedidos = []

    def get_json(self, url, params=None):
        params = params or {}
        if url == f"{SICONFI}/entes":
            return {"items": [{"cod_ibge": 1200013, "ente": "Acrelândia", "uf": "AC", "esfera": "M", "populacao": 15000}]}
        self.pedidos.append(params.get("me_referencia"))
        return {"items": ITENS if params.get("me_referencia") in (1, 2) else [], "hasMore": False}

    def get_bytes(self, url, params=None):
        raise RuntimeError("404")


def test_gerar(tmp_path):
    c = Cliente()
    r = mensal.gerar(lambda: c, tmp_path, anos=[2026], ufs=["AC"], hoje=date(2026, 4, 10), trabalhadores=1)
    assert c.pedidos == [1, 2, 3]
    assert r == {"meses_siconfi": 2, "meses_reaproveitados": 0, "arquivos": 1}
    doc = md.ler((tmp_path / "v1/municipios/ac/1200013/2026-mensal.md").read_text())
    assert doc.meta["tipo"] == "municipio-mensal"
    assert [m["mes"] for m in doc.tabelas["meses"]] == ["1", "2"]
    assert doc.tabelas["meses"][0]["arrecadado"] == "3550"
    assert {a["area"] for a in doc.tabelas["areas-mes"]} == {"Saúde", "Educação"}
