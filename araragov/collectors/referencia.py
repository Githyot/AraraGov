"""Dados de referência: IPCA (Banco Central) e tabela de subsídios (salários).

O subsídio de deputados e senadores é fixado por decreto legislativo e não
tem API. A tabela fica em araragov/referencia/subsidios.csv, com o ato e a
fonte de cada valor, para qualquer pessoa conferir.
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from importlib import resources

from sqlalchemy import delete, insert

from ..db import Ipca, Subsidio, sessao
from ..http import HttpClient
from .. import normalizar as n

logger = logging.getLogger(__name__)

# Série 433 do SGS/BCB: IPCA, variação % mensal. A API limita 10 anos por consulta.
IPCA_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
IPCA_INICIO = 2010


def coletar_ipca(client: HttpClient, ate: date | None = None) -> int:
    ate = ate or date.today()
    linhas = {}
    inicio = IPCA_INICIO
    while inicio <= ate.year:
        fim = min(inicio + 9, ate.year)
        dados = client.get_json(
            IPCA_URL,
            {"formato": "json", "dataInicial": f"01/01/{inicio}", "dataFinal": f"31/12/{fim}"},
        )
        for item in dados:
            competencia = n.data(item.get("data"))
            variacao = n.decimal(item.get("valor"))
            if competencia and variacao is not None:
                linhas[competencia] = variacao
        inicio = fim + 1
    with sessao() as s:
        s.execute(delete(Ipca))
        if linhas:
            s.execute(insert(Ipca), [{"competencia": k, "variacao": v} for k, v in sorted(linhas.items())])
    logger.info("IPCA: %s meses gravados", len(linhas))
    return len(linhas)


def carregar_subsidios() -> int:
    arquivo = resources.files("araragov").joinpath("referencia/subsidios.csv")
    with arquivo.open(encoding="utf-8") as f:
        linhas = [
            {
                "cargo": r["cargo"],
                "vigencia_inicio": date.fromisoformat(r["vigencia_inicio"]),
                "valor": n.decimal(r["valor"]),
                "ato": r["ato"],
                "fonte": r["fonte"],
            }
            for r in csv.DictReader(f)
        ]
    with sessao() as s:
        s.execute(delete(Subsidio))
        s.execute(insert(Subsidio), linhas)
    logger.info("Subsídios: %s valores gravados", len(linhas))
    return len(linhas)
