from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from araragov.municipios import md

EXEMPLO = Path(__file__).parent / "fixtures" / "formato-md-exemplo.md"


def test_le_exemplo():
    doc = md.ler(EXEMPLO.read_text(encoding="utf-8"))
    assert doc.meta["tipo"] == "municipio-ano"
    assert doc.meta["municipio"] == "Campo Mourão"
    gastos = doc.tabelas["gastos-area"]
    assert len(gastos) == 3
    assert md.numero(gastos[0]["valor_pago"]) == Decimal("18234567.89")
    assert gastos[2]["subarea"] is None
    assert doc.tabelas["pagamentos"][0]["favorecido"] == "Empresa | Exemplo Ltda"
    assert doc.colunas["pagamentos"] == ["cnpj", "favorecido", "valor", "data"]
    falta = doc.tabelas["sem-dados"][0]
    assert falta["esfera"] == "municipal" and falta["secao"] == "salarios"


def test_ida_e_volta():
    texto = md.escrever(
        {"tipo": "teste", "ano": 2024, "atualizado": date(2026, 11, 5)},
        {
            "itens": [
                {"nome": "Poste | LED", "valor": Decimal("1500.00"), "obs": None},
                {"nome": "Asfalto\nCBUQ", "valor": 87.5, "obs": "m²"},
            ]
        },
        titulo="Teste",
        textos={"itens": "## Itens"},
    )
    doc = md.ler(texto)
    assert doc.meta == {"formato": md.FORMATO, "tipo": "teste", "ano": "2024", "atualizado": "2026-11-05"}
    itens = doc.tabelas["itens"]
    assert itens[0] == {"nome": "Poste | LED", "valor": "1500", "obs": None}
    assert itens[1] == {"nome": "Asfalto CBUQ", "valor": "87.5", "obs": "m²"}


def test_numeros_sem_notacao_cientifica():
    texto = md.escrever({"tipo": "t"}, {"n": [{"v": Decimal("120000.00")}, {"v": Decimal("0.001")}]})
    assert "| 120000 |" in texto and "| 0.001 |" in texto


@pytest.mark.parametrize(
    "texto",
    [
        "sem cabeçalho",
        "---\nformato: outro/1\ntipo: t\n---\n",
        "---\nformato: araragov-md/1\n---\n",
        "---\nformato: araragov-md/1\ntipo: t\n---\n<!-- tabela: a -->\n| x | y |\n|---|---|\n| 1 |\n",
        "---\nformato: araragov-md/1\ntipo: t\n---\n<!-- tabela: a -->\n| x |\n| 1 |\n",
        "---\nformato: araragov-md/1\ntipo: t\n---\n<!-- tabela: a -->\n| x |\n|---|\n<!-- tabela: a -->\n| x |\n|---|\n",
    ],
)
def test_rejeita_invalido(texto):
    with pytest.raises(md.ErroFormato):
        md.ler(texto)


def test_escrever_rejeita_coluna_nao_declarada():
    with pytest.raises(md.ErroFormato):
        md.escrever({"tipo": "t"}, {"a": [{"x": 1}, {"y": 2}]}, colunas={"a": ["x"]})
