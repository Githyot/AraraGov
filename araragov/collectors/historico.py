"""Histórico entre coletas.

O banco é recriado a cada coleta, mas alguns dados são caros de buscar de
novo (uma página por deputado e ano) e não mudam depois que o ano fecha. A
exportação publica esses dados em v1/historico/recursos.json; a coleta
seguinte começa lendo esse arquivo da API publicada e só busca o que falta.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import insert

from ..db import Beneficio, Despesa, RecursoMensal, sessao
from ..http import HttpClient

logger = logging.getLogger(__name__)

API_PUBLICA = os.environ.get("ARARAGOV_API_PUBLICA", "https://githyot.github.io/AraraGov/v1")
ARQUIVO = "historico/recursos.json"
CAMPOS_RECURSO = ("casa", "codigo_politico", "tipo", "ano", "mes", "valor")
CAMPOS_DESPESA = ("casa", "chave_fonte", "codigo_politico", "nome_politico", "ano", "mes", "categoria",
                  "fornecedor", "cnpj_cpf", "data_documento", "valor", "url_documento")
# Despesas que só se conseguem com um pedido por deputado e mês (ALMG: 77 deputados x 12 meses
# por ano). As outras casas publicam o ano inteiro num arquivo só e são baixadas de novo.
DESPESAS_REAPROVEITADAS = ("al-mg",)
MES_FECHAMENTO = 4

# (casa, ano) cujas despesas vieram da coleta anterior; o coletor pula esses anos.
anos_carregados: set = set()


def ano_fechado(ano: int, hoje: Optional[date] = None) -> bool:
    """O ano não muda mais a partir de abril do ano seguinte."""
    hoje = hoje or date.today()
    return ano < hoje.year - 1 or (ano == hoje.year - 1 and hoje.month >= MES_FECHAMENTO)


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
    despesas = []
    for linha in dados.get("despesas") or []:
        d = dict(zip(CAMPOS_DESPESA, linha))
        if d["casa"] not in DESPESAS_REAPROVEITADAS or not ano_fechado(d["ano"]):
            continue
        d["valor"] = Decimal(str(d["valor"]))
        d["data_documento"] = date.fromisoformat(d["data_documento"]) if d["data_documento"] else None
        despesas.append(d)
        anos_carregados.add((d["casa"], d["ano"]))
    with sessao() as s:
        if despesas:
            s.execute(insert(Despesa), despesas)
        if recursos:
            s.execute(insert(RecursoMensal), recursos)
        if beneficios:
            s.execute(insert(Beneficio), beneficios)
    logger.info("Histórico: %s valores mensais, %s benefícios e %s despesas da coleta anterior",
                len(recursos), len(beneficios), len(despesas))
    return len(recursos)
