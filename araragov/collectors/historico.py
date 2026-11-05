"""Histórico entre coletas.

O banco é recriado a cada coleta, mas alguns dados são caros de buscar de
novo (uma página por deputado e ano) e não mudam depois que o ano fecha. A
exportação publica esses dados em v1/historico/recursos.json; a coleta
seguinte começa lendo esse arquivo da API publicada e só busca o que falta.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal

from sqlalchemy import insert

from ..db import Beneficio, RecursoMensal, sessao
from ..http import HttpClient

logger = logging.getLogger(__name__)

API_PUBLICA = os.environ.get("ARARAGOV_API_PUBLICA", "https://githyot.github.io/AraraGov/v1")
ARQUIVO = "historico/recursos.json"
CAMPOS_RECURSO = ("casa", "codigo_politico", "tipo", "ano", "mes", "valor")


def carregar(client: HttpClient, base: str = API_PUBLICA) -> int:
    dados = client.get_json(f"{base}/{ARQUIVO}")
    recursos = [
        {**dict(zip(CAMPOS_RECURSO, linha)), "valor": Decimal(str(linha[5])), "disponivel": None}
        for linha in dados.get("recursos") or []
    ]
    beneficios = [
        {**b, "valor_mensal": None, "valor_ano": None if b.get("valor_ano") is None else Decimal(str(b["valor_ano"]))}
        for b in dados.get("beneficios") or []
    ]
    with sessao() as s:
        if recursos:
            s.execute(insert(RecursoMensal), recursos)
        if beneficios:
            s.execute(insert(Beneficio), beneficios)
    logger.info("Histórico: %s valores mensais e %s benefícios da coleta anterior", len(recursos), len(beneficios))
    return len(recursos)
