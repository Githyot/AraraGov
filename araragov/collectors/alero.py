"""Assembleia Legislativa de Rondônia (ALE-RO).

A página de dados abertos do portal da transparência
(https://transparencia.al.ro.leg.br/DadosAbertos/) documenta a API
/api/servidores, que devolve nome, cargo e lotação de cada servidor em JSON
e aceita filtro por lotação. As pessoas lotadas em "GAB. DEP. NOME" formam a
equipe do gabinete. A API não traz remuneração. O robots.txt só bloqueia
/admin/ e /painel/.

A página da verba indenizatória do portal vem sem dados quando acessada
fora do navegador, por isso os gastos de Rondônia não são coletados.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import delete, insert, select

from ..db import Assessor, Politico, sessao
from ..http import HttpClient
from ._comum import casar_nome

logger = logging.getLogger(__name__)

CASA = "al-ro"
PORTAL = "https://transparencia.al.ro.leg.br"
SERVIDORES = PORTAL + "/api/servidores?lotacao=GAB.%20DEP"
GABINETE = re.compile(r"^\s*GAB(INETE)?\.?\s*(DO\s+|DA\s+)?DEP(UTAD[OA])?\.?\s+(.+?)\s*$", re.I)


def agrupar(servidores: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grupos: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in servidores:
        m = GABINETE.match(p.get("dsclotacao") or "")
        if m and (p.get("nome") or "").strip():
            grupos[m.group(4)].append(p)
    return grupos


def coletar_gabinetes(client: HttpClient) -> int:
    from .tse import _titulo

    servidores = json.loads(client.get_bytes(SERVIDORES).decode("utf-8"))
    grupos = agrupar(servidores)
    if len(grupos) < 15:
        raise RuntimeError(f"API de servidores da ALE-RO com só {len(grupos)} gabinetes")
    with sessao() as s:
        candidatos = {cod: [nome, civil] for cod, nome, civil in s.execute(
            select(Politico.codigo, Politico.nome, Politico.nome_civil).where(Politico.casa == CASA)).all()}
    linhas: List[Dict[str, Any]] = []
    sem_dono = []
    for deputado, pessoas in sorted(grupos.items()):
        cod = casar_nome(deputado, candidatos)
        if cod is None:
            sem_dono.append(deputado)
            continue
        for p in pessoas:
            linhas.append({
                "casa": CASA, "codigo_politico": cod, "nome": _titulo(p["nome"].strip()),
                "cargo": (p.get("dsccargo") or "").strip() or None, "funcao": None,
                "lotacao": p["dsclotacao"].strip(),
            })
    with sessao() as s:
        s.execute(delete(Assessor).where(Assessor.casa == CASA))
        if linhas:
            s.execute(insert(Assessor), linhas)
    logger.info("ALE-RO: %s pessoas em %s gabinetes; gabinetes sem deputado ligado: %s", len(linhas), len(grupos) - len(sem_dono), ", ".join(sem_dono) or "nenhum")
    return len(linhas)
