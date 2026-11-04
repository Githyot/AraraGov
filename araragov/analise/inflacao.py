"""Custo x inflação: o gasto ou o salário subiu mais ou menos que o IPCA?"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Optional

from sqlalchemy import func, select

from ..db import Despesa, Ipca, Subsidio, sessao


def _mes(d: date) -> date:
    return date(d.year, d.month, 1)


def fator_ipca(ipca: Mapping[date, Decimal], de: date, ate: date) -> Decimal:
    """Fator de correção acumulado dos meses depois de `de` até `ate`, inclusive.

    Ex.: de=jan/2024, ate=mar/2024 aplica a inflação de fev e mar.
    """
    fator = Decimal(1)
    for competencia, variacao in ipca.items():
        if _mes(de) < competencia <= _mes(ate):
            fator *= 1 + variacao / 100
    return fator


@dataclass
class Comparacao:
    referencia: date
    valor_referencia: Decimal
    data: date
    valor_real: Decimal
    valor_corrigido: Decimal  # quanto seria se tivesse subido só pela inflação

    @property
    def acima_da_inflacao_pct(self) -> Decimal:
        """Positivo: subiu mais que a inflação. Negativo: subiu menos."""
        return (self.valor_real / self.valor_corrigido - 1) * 100


def comparar(ipca: Mapping[date, Decimal], de: date, valor_de: Decimal, ate: date, valor_ate: Decimal) -> Comparacao:
    corrigido = (valor_de * fator_ipca(ipca, de, ate)).quantize(Decimal("0.01"))
    return Comparacao(de, valor_de, ate, valor_ate, corrigido)


def carregar_ipca() -> Dict[date, Decimal]:
    with sessao() as s:
        return dict(s.execute(select(Ipca.competencia, Ipca.variacao)).all())


def subsidio_em(cargo: str, quando: date) -> Optional[Decimal]:
    with sessao() as s:
        return s.execute(
            select(Subsidio.valor)
            .where(Subsidio.cargo == cargo, Subsidio.vigencia_inicio <= quando)
            .order_by(Subsidio.vigencia_inicio.desc())
            .limit(1)
        ).scalar_one_or_none()


def subsidio_vs_inflacao(cargo: str, de: date, ate: date) -> Optional[Comparacao]:
    valor_de, valor_ate = subsidio_em(cargo, de), subsidio_em(cargo, ate)
    if valor_de is None or valor_ate is None:
        return None
    return comparar(carregar_ipca(), de, valor_de, ate, valor_ate)


def gastos_anuais(casa: str, codigo_politico: int) -> Dict[int, Decimal]:
    with sessao() as s:
        linhas = s.execute(
            select(Despesa.ano, func.sum(Despesa.valor))
            .where(Despesa.casa == casa, Despesa.codigo_politico == codigo_politico)
            .group_by(Despesa.ano)
            .order_by(Despesa.ano)
        ).all()
    return {ano: Decimal(total) for ano, total in linhas}


def gastos_vs_inflacao(casa: str, codigo_politico: int) -> List[Comparacao]:
    """Compara o gasto de cada ano com o do primeiro ano corrigido pelo IPCA."""
    anos = gastos_anuais(casa, codigo_politico)
    if len(anos) < 2:
        return []
    ipca = carregar_ipca()
    primeiro = min(anos)
    base = date(primeiro, 12, 1)
    return [
        comparar(ipca, base, anos[primeiro], date(ano, 12, 1), anos[ano])
        for ano in sorted(anos)
        if ano != primeiro
    ]
