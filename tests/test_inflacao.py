from datetime import date
from decimal import Decimal

from araragov.analise import inflacao
from araragov.collectors import referencia


def test_fator_ipca_aplica_meses_seguintes():
    ipca = {date(2024, 1, 1): Decimal("0.42"), date(2024, 2, 1): Decimal("0.83"), date(2024, 3, 1): Decimal("0.16")}
    fator = inflacao.fator_ipca(ipca, date(2024, 1, 15), date(2024, 3, 1))
    assert fator == Decimal("1.0083") * Decimal("1.0016")


def test_comparacao_acima_da_inflacao():
    ipca = {date(2024, 2, 1): Decimal("10")}
    c = inflacao.comparar(ipca, date(2024, 1, 1), Decimal("100"), date(2024, 2, 1), Decimal("121"))
    assert c.valor_corrigido == Decimal("110.00")
    assert round(c.acima_da_inflacao_pct, 2) == Decimal("10.00")


def test_subsidio_vs_inflacao_com_tabela_oficial(client):
    referencia.carregar_subsidios()
    client.json(referencia.IPCA_URL, "ipca.json")
    referencia.coletar_ipca(client, ate=date(2024, 3, 31))
    assert inflacao.subsidio_em("Deputado Federal", date(2024, 3, 1)) == Decimal("44008.52")
    c = inflacao.subsidio_vs_inflacao("Deputado Federal", date(2024, 1, 1), date(2024, 3, 1))
    # jan->mar/2024: salário subiu 5,66% (41.650,92 -> 44.008,52); IPCA de fev+mar ~0,99%
    assert c.acima_da_inflacao_pct > Decimal("4.5")


def test_comparar_anos_ajusta_meses_da_posse_e_do_ano_em_andamento():
    ipca = {date(2024, 6, 1): Decimal("10")}
    anos = {2023: Decimal("1100"), 2024: Decimal("1200"), 2025: Decimal("500")}
    # 2023 começou em fevereiro (11 meses); 2025 vai só até maio.
    meses = {2023: (2, 12), 2024: (1, 12), 2025: (1, 5)}
    c24, c25 = inflacao.comparar_anos(ipca, anos, meses, hoje=date(2025, 6, 10))
    assert (c24.meses_base, c24.meses, c24.parcial) == (11, 12, False)
    assert c24.valor_corrigido == Decimal("1320.00")  # 1100/11*12 * 1,10
    assert c25.parcial and c25.meses == 5
    assert c25.valor_corrigido == Decimal("550.00")  # 1100/11*5 * 1,10
    assert round(c25.acima_da_inflacao_pct, 2) == Decimal("-9.09")


def test_comparar_anos_passados_contam_ano_inteiro():
    anos = {2023: Decimal("100"), 2024: Decimal("50")}
    meses = {2023: (1, 12), 2024: (1, 3)}  # só gastou até março, mas o ano acabou
    (c,) = inflacao.comparar_anos({}, anos, meses, hoje=date(2026, 1, 1))
    assert not c.parcial and c.valor_corrigido == Decimal("100.00")
