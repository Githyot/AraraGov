"""Gera v1/referencia/custos/{uf}.md (fase 3 de docs/municipios.md)."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, Optional

from .. import normalizar as n
from ..collectors.referencia import IPCA_URL
from . import custos, sidra

logger = logging.getLogger(__name__)


def ipca_anual(client, desde: int, ate: int) -> Dict[int, Decimal]:
    """Índice acumulado do IPCA (base 1 em jan/desde), média de cada ano."""
    meses = []
    inicio = desde
    while inicio <= ate:
        fim = min(inicio + 9, ate)
        meses += client.get_json(IPCA_URL, {"formato": "json", "dataInicial": f"01/01/{inicio}", "dataFinal": f"31/12/{fim}"})
        inicio = fim + 1
    indice, por_ano = Decimal(1), {}
    for d, v in sorted((n.data(m.get("data")), n.decimal(m.get("valor"))) for m in meses):
        if d and v is not None:
            indice *= 1 + v / 100
            por_ano.setdefault(d.year, []).append(indice)
    return {a: sum(vs) / len(vs) for a, vs in por_ano.items()}


def gerar(client, saida: Path, ufs: Iterable[str], anos: Iterable[int], hoje: Optional[date] = None) -> int:
    hoje = hoje or date.today()
    anos = sorted(anos)
    try:
        mensal = sidra.custo_medio(client)
    except Exception as erro:  # sem o SIDRA, sobram as fontes curadas e o IPCA
        logger.warning("SIDRA indisponível: %s", erro)
        mensal = {}
    try:
        ipca = ipca_anual(client, anos[0] - custos.ANOS_MAX_ESTICAR, hoje.year)
    except Exception as erro:
        logger.warning("IPCA indisponível: %s", erro)
        ipca = {}
    calc = custos.calculadora_padrao(sidra.observacoes(mensal), sidra.indices_anuais(mensal), ipca)
    pasta = saida / "v1" / "referencia" / "custos"
    pasta.mkdir(parents=True, exist_ok=True)
    for uf in ufs:
        (pasta / f"{uf.lower()}.md").write_text(custos.documento_uf(calc, uf.upper(), anos, hoje), encoding="utf-8")
    logger.info("Custos de referência: %s estados, anos %s-%s", len(list(ufs)), anos[0], anos[-1])
    return len(list(ufs))
