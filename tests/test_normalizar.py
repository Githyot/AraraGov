from decimal import Decimal

import pytest

from araragov import normalizar as n


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Sim", "sim"),
        ("Não", "nao"),
        ("NAO", "nao"),
        ("Abstenção", "abstencao"),
        ("Obstrução", "obstrucao"),
        ("Artigo 17", "presidente"),
        ("Presidente (art. 51 RISF)", "presidente"),
        ("NCom", "ausente"),
        ("P-NRV", "presente_sem_voto"),
        ("LP", "licenca"),
        ("MIS", "missao"),
        (None, "ausente"),
        ("algo novo", "outro"),
    ],
)
def test_voto(entrada, esperado):
    assert n.voto(entrada) == esperado


def test_decimal_formatos():
    assert n.decimal("104.58") == Decimal("104.58")
    assert n.decimal("1.234,56") == Decimal("1234.56")
    assert n.decimal("0,42") == Decimal("0.42")
    assert n.decimal("") is None


def test_datas():
    assert n.data("01/02/2024").isoformat() == "2024-02-01"
    assert n.data_hora("2025-03-11T20:15:02").hour == 20


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("ANDRÉ ABDON", "André Abdon"),
        ("JOSÉ DA SILVA E SOUZA", "José da Silva e Souza"),
        ("MARIA-JOSÉ DOS SANTOS", "Maria-José dos Santos"),
        ("AJ Albuquerque", "AJ Albuquerque"),
        ("Abel Rebouças", "Abel Rebouças"),
        (None, None),
    ],
)
def test_nome_proprio(entrada, esperado):
    assert n.nome_proprio(entrada) == esperado
