from datetime import date
from decimal import Decimal as D

from araragov.municipios import custos, md
from araragov.municipios.custos import Calculadora, Componente, Item, Observacao, PeriodoAtipico

ITENS = {
    "asfalto": Item("asfalto", "CBUQ 5 cm", "m²", "pavimentacao"),
    "cbuq-t": Item("cbuq-t", "Massa asfáltica", "t", "insumo"),
    "frete-t": Item("frete-t", "Frete por t", "t", "insumo"),
    "capa": Item("capa", "Capa montada", "m²", "pavimentacao"),
}


def _o(item, uf, comp, valor, origem="artigo"):
    return Observacao(item, uf, comp, D(valor), origem, "Fonte X", "https://exemplo.invalid/x")


def test_nivel1_faixa_e_descarte_de_extremos():
    obs = [_o("asfalto", "PR", "2023-06", v) for v in ("10", "90", "100", "110", "500")]
    r = Calculadora(ITENS, obs).referencia("asfalto", "PR", 2023)
    assert r.nivel == 1 and (r.minimo, r.mediana, r.maximo) == (D("90.00"), D("100.00"), D("110.00"))
    assert r.comparar(D("150")) == ("acima", D("36.4"))
    assert r.comparar(D("100"))[0] == "dentro"


def test_fonte_unica_ganha_faixa_minima():
    r = Calculadora(ITENS, [_o("asfalto", "PR", "2023-06", "100")]).referencia("asfalto", "PR", 2023)
    assert (r.minimo, r.maximo) == (D("90.00"), D("110.00"))


def test_nivel2_composicao_com_bdi():
    obs = [_o("cbuq-t", "PR", "2023-01", "500"), _o("frete-t", "PR", "2023-01", "50")]
    comp = [Componente("capa", "cbuq-t", D("0.12")), Componente("capa", "frete-t", D("0.12"))]
    r = Calculadora(ITENS, obs, comp).referencia("capa", "PR", 2023)
    assert r.nivel == 2
    # 0,12 × (500 + 50) = 66; faixa de cada parte ±10%; BDI 20% a 28%
    assert r.minimo == D("71.28") and r.maximo == D("92.93")
    assert "BDI" in r.metodo


def test_nivel3_outro_ano_pelo_indice_e_vizinho():
    obs = [_o("asfalto", "PR", "2021-06", "100")]
    indices = {("PR", 2021): D("1.0"), ("PR", 2023): D("1.2"), ("SC", 2021): D("1.1")}
    calc = Calculadora(ITENS, obs, indices=indices)
    r = calc.referencia("asfalto", "PR", 2023)
    assert r.nivel == 3 and r.mediana == D("120.00") and "índice de custo" in r.metodo
    assert r.minimo == D("97.20") and r.maximo == D("145.20")  # ±10% e mais 10% (2 anos)
    v = calc.referencia("asfalto", "SC", 2021)
    assert v.nivel == 3 and v.mediana == D("110.00") and "PR 2021" in v.metodo


def test_nivel3_sem_indice_usa_ipca_com_aviso():
    calc = Calculadora(ITENS, [_o("asfalto", "PR", "2019-06", "100")], ipca_anual={2019: D("1"), 2020: D("1.05")})
    r = calc.referencia("asfalto", "PR", 2020)
    assert r.mediana == D("105.00") and any("IPCA" in a for a in r.avisos)


def test_periodo_atipico_alarga_e_avisa():
    atip = [PeriodoAtipico("2020-03", "2022-05", (), (), "Pandemia", "Lei 13.979/2020")]
    r = Calculadora(ITENS, [_o("asfalto", "PR", "2021-06", "100")], atipicos=atip).referencia("asfalto", "PR", 2021)
    assert (r.minimo, r.maximo) == (D("81.00"), D("121.00")) and "Pandemia" in r.avisos[0]
    assert Calculadora(ITENS, [_o("asfalto", "PR", "2019-06", "100")], atipicos=atip).referencia("asfalto", "PR", 2019).avisos == []


def test_sem_dado_nao_inventa():
    assert Calculadora(ITENS, []).referencia("asfalto", "PR", 2023) is None
    # longe demais no tempo
    assert Calculadora(ITENS, [_o("asfalto", "PR", "2010-01", "1")]).referencia("asfalto", "PR", 2023) is None


def test_tabelas_curadas_e_documento():
    calc = custos.calculadora_padrao(observacoes_extras=[_o("creche", "PR", "2023-03", "4000", "tabela-oficial")],
                                    ipca_anual={2021: D("1"), 2023: D("1.1")})
    assert "pavimentacao-cbuq" in calc.itens and calc.atipicos
    texto = custos.documento_uf(calc, "PR", [2021, 2023], hoje=date(2026, 11, 5))
    doc = md.ler(texto)
    refs = {(r["item"], r["ano"]): r for r in doc.tabelas["referencias"]}
    assert refs[("creche", "2023")]["nivel"] == "1" and refs[("creche", "2021")]["nivel"] == "3"
    assert "Pandemia" in refs[("creche", "2021")]["avisos"]
    assert any(p["ufs"] == "Brasil" for p in doc.tabelas["periodos-atipicos"])
    assert all(p["ufs"] != "RS" for p in doc.tabelas["periodos-atipicos"])
