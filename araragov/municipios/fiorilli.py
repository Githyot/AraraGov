"""Portais de transparência de prefeituras feitos pela Fiorilli (sistema SCPI).

Muitas prefeituras de estados cujo tribunal de contas não publica dados
abertos (GO, MG, PR, RS, MS, TO...) usam o portal da Fiorilli. Todos têm a
mesma API JSON, em `{site}/Transparencia/VersaoJson/...`, documentada pela
própria Fiorilli ("Dados Abertos Portal Transparência Fiorilli"). A lista de
endpoints e os nomes de campo foram conferidos no projeto Mais Transparência
(github.com/maistransparencia/transparencia, AGPL-3.0).

Não existe uma lista pública dos clientes. `descobrir` testa, para cada
município, os endereços mais comuns do portal e guarda os que respondem em
`araragov/referencia/fiorilli.csv`. Portais atrás de proteção contra robôs
(Cloudflare) ficam de fora: o AraraGov não contorna bloqueios.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import requests

from ..config import USER_AGENT
from .eleitos import municipios_ibge

logger = logging.getLogger(__name__)

CAMINHO = "/Transparencia/VersaoJson/Despesas/"
COLUNAS = ["uf", "ibge", "municipio", "site"]


def _slug(nome: str) -> str:
    from .eleitos import chave_nome

    return chave_nome(nome).lower().replace(" ", "")


def candidatos(uf: str, nome: str) -> List[str]:
    """Endereços em que o portal Fiorilli costuma ficar."""
    s, u = _slug(nome), uf.lower()
    return [
        f"https://transparencia.{s}.{u}.gov.br",
        f"https://{s}.{u}.gov.br",
        f"https://www.{s}.{u}.gov.br",
        f"http://{s}.{u}.gov.br:8079",
        f"http://transparencia.{s}.{u}.gov.br:8079",
    ]


def _parece_fiorilli(texto: str) -> bool:
    t = texto.lstrip()
    if not t.startswith(("[", "{")):
        return False  # página HTML, inclusive o desafio do Cloudflare
    try:
        json.loads(t)
    except ValueError:
        return False
    return True


def responde(sessao, site: str, ano: int, tempo: float = 8) -> bool:
    try:
        r = sessao.get(f"{site}{CAMINHO}", params={"Listagem": "DefineExercicio", "ConectarExercicio": ano},
                       timeout=tempo, allow_redirects=True)
    except requests.RequestException:
        return False
    return r.status_code == 200 and _parece_fiorilli(r.text)


def descobrir(ufs: Optional[Iterable[str]] = None, ano: Optional[int] = None, trabalhadores: int = 48,
              sessao=None) -> List[Dict[str, str]]:
    """Testa os endereços comuns de cada município e devolve os portais Fiorilli que responderam."""
    ano = ano or date.today().year - 1
    filtro = {u.upper() for u in ufs} if ufs else None
    sessao = sessao or requests.Session()
    sessao.headers.setdefault("User-Agent", USER_AGENT)
    municipios = sorted((uf, cod, nome) for (uf, _), (cod, nome) in municipios_ibge().items()
                        if filtro is None or uf in filtro)

    def um(m: Tuple[str, int, str]) -> Optional[Dict[str, str]]:
        uf, cod, nome = m
        for site in candidatos(uf, nome):
            if responde(sessao, site, ano):
                return {"uf": uf, "ibge": str(cod), "municipio": nome, "site": site}
        return None

    with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
        achados = [a for a in ex.map(um, municipios) if a]
    logger.info("Fiorilli: %s portais em %s municípios testados", len(achados), len(municipios))
    return achados


def escrever_lista(achados: List[Dict[str, str]]) -> str:
    saida = io.StringIO()
    saida.write("# Portais Fiorilli encontrados por araragov fiorilli-descobrir\n")
    w = csv.DictWriter(saida, fieldnames=COLUNAS, delimiter=";", lineterminator="\n")
    w.writeheader()
    for a in sorted(achados, key=lambda a: (a["uf"], int(a["ibge"]))):
        w.writerow(a)
    return saida.getvalue()
