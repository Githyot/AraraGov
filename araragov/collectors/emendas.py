"""Emendas parlamentares ao orçamento federal.

Fonte: Portal da Transparência (CGU), arquivo único com todas as emendas
desde 2014: https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares

- EmendasParlamentares.csv: uma linha por emenda e localidade, com valores
  empenhados e pagos (acumulados).
- EmendasParlamentares_PorFavorecido.csv: quem recebeu o dinheiro (empresa,
  prefeitura, entidade), por mês.

O autor vem pelo nome parlamentar ("PATRUS ANANIAS"), que é casado com
deputados e senadores do banco. Emendas de bancada, comissão e relator não
têm um autor só e ficam sem parlamentar. Pessoas físicas que receberam
recursos aparecem somadas numa linha só, sem nome nem documento.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterator, List, Optional, Tuple

from sqlalchemy import delete, insert, select

from ..db import Emenda, Favorecido, Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from .gabinete import _chave_nome

logger = logging.getLogger(__name__)

EMENDAS_URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
ARQ_EMENDAS = "EmendasParlamentares.csv"
ARQ_FAVORECIDOS = "EmendasParlamentares_PorFavorecido.csv"

_cache: Dict[int, bytes] = {}


def _zip(client: HttpClient) -> zipfile.ZipFile:
    chave = id(client)
    if chave not in _cache:
        _cache.clear()
        _cache[chave] = client.get_bytes(EMENDAS_URL)
    return zipfile.ZipFile(io.BytesIO(_cache[chave]))


def _linhas(z: zipfile.ZipFile, nome: str) -> Iterator[Dict[str, str]]:
    with z.open(nome) as bruto:
        yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")


def _autores() -> Dict[str, Optional[Tuple[str, int]]]:
    """Nome normalizado -> (casa, código). Nomes repetidos entre parlamentares
    viram None, para não atribuir a emenda à pessoa errada."""
    with sessao() as s:
        linhas = s.execute(
            select(Politico.nome, Politico.casa, Politico.codigo).where(Politico.casa.in_(("camara", "senado")))
        ).all()
    mapa: Dict[str, Optional[Tuple[str, int]]] = {}
    for nome, casa, cod in linhas:
        chave = _chave_nome(nome or "")
        if not chave:
            continue
        mapa[chave] = None if chave in mapa and mapa[chave] != (casa, cod) else (casa, cod)
    return mapa


def coletar_emendas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    z = _zip(client)
    autores = _autores()

    # O mesmo código aparece em várias linhas (uma por localidade/ação): soma.
    emendas: Dict[str, dict] = {}
    for r in _linhas(z, ARQ_EMENDAS):
        if n.inteiro(r.get("Ano da Emenda")) != ano:
            continue
        codigo = (r.get("Código da Emenda") or "").strip()
        if not codigo or codigo.lower().startswith("sem"):
            continue
        empenhado = n.decimal(r.get("Valor Empenhado")) or Decimal(0)
        pago = n.decimal(r.get("Valor Pago")) or Decimal(0)
        if codigo in emendas:
            emendas[codigo]["empenhado"] += empenhado
            emendas[codigo]["pago"] += pago
            continue
        if limite and len(emendas) >= limite:
            continue
        autor = n.texto(r.get("Nome do Autor da Emenda"))
        dono = autores.get(_chave_nome(autor or ""))
        emendas[codigo] = {
            "codigo": codigo,
            "ano": ano,
            "tipo": n.texto(r.get("Tipo de Emenda")),
            "autor": autor,
            "casa": dono[0] if dono else None,
            "codigo_politico": dono[1] if dono else None,
            "localidade": n.texto(r.get("Localidade de aplicação do recurso")),
            "uf": n.texto(r.get("UF")),
            "funcao": n.texto(r.get("Nome Função")),
            "acao": n.texto(r.get("Nome Ação")),
            "empenhado": empenhado,
            "pago": pago,
        }

    # Favorecidos das emendas deste ano, somados por parlamentar e favorecido.
    dono_da_emenda = {c: (e["casa"], e["codigo_politico"]) for c, e in emendas.items() if e["codigo_politico"]}
    somas: Dict[tuple, Decimal] = defaultdict(Decimal)
    info: Dict[tuple, dict] = {}
    for r in _linhas(z, ARQ_FAVORECIDOS):
        dono = dono_da_emenda.get((r.get("Código da Emenda") or "").strip())
        if not dono:
            continue
        valor = n.decimal(r.get("Valor Recebido")) or Decimal(0)
        pessoa_fisica = "física" in (r.get("Tipo Favorecido") or "").lower()
        if pessoa_fisica:
            chave = (*dono, "Pessoas físicas (somadas)", None)
        else:
            chave = (*dono, n.texto(r.get("Favorecido")) or "Não informado", n.texto(r.get("Código do Favorecido")))
        somas[chave] += valor
        info.setdefault(chave, {
            "tipo": n.texto(r.get("Tipo Favorecido")),
            "municipio": None if pessoa_fisica else n.texto(r.get("Município Favorecido")),
            "uf": None if pessoa_fisica else n.texto(r.get("UF Favorecido")),
        })
    favorecidos = [
        {"casa": casa, "codigo_politico": cod, "ano": ano, "nome": nome, "documento": doc, "valor": valor, **info[(casa, cod, nome, doc)]}
        for (casa, cod, nome, doc), valor in somas.items()
    ]

    with sessao() as s:
        s.execute(delete(Emenda).where(Emenda.ano == ano))
        s.execute(delete(Favorecido).where(Favorecido.ano == ano))
        if emendas:
            s.execute(insert(Emenda), list(emendas.values()))
        if favorecidos:
            s.execute(insert(Favorecido), favorecidos)
    com_autor = sum(1 for e in emendas.values() if e["codigo_politico"])
    logger.info(
        "Emendas %s: %s emendas, %s ligadas a um parlamentar, %s favorecidos",
        ano, len(emendas), com_autor, len(favorecidos),
    )
    return len(emendas)
