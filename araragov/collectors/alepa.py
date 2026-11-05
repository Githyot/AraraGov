"""Assembleia Legislativa do Pará (Alepa).

A Alepa publica a "Verba de Gabinete" em
https://sigep.alepa.pa.gov.br/transp/frame_verbagabinete.php (página aberta
dentro do portal da transparência): uma linha por gabinete com o mês de
referência, quantos assessores há e o total pago, e um link de detalhamento
com nome, cargo e valor de cada pessoa. O CPF vem mascarado e não é gravado.
O site não tem robots.txt.

A verba indenizatória do Pará fica num painel interativo (Quartertec) sem
arquivo para baixar, por isso não é coletada.
"""

from __future__ import annotations

import html as h
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select

from ..db import Assessor, Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import casar_nome

logger = logging.getLogger(__name__)

CASA = "al-pa"
BASE = "https://sigep.alepa.pa.gov.br/transp/"
GABINETES = BASE + "frame_verbagabinete.php"
MESES = {m: i for i, m in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"], 1)}


def _celulas(linha: str) -> List[str]:
    return [" ".join(h.unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)]


def _referencia(texto: str) -> Optional[str]:
    m = re.match(r"\s*([A-Za-zçÇ]+)\s*/\s*(\d{4})", texto)
    if not m:
        return None
    mes = MESES.get(m.group(1).lower().replace("ç", "c"))
    return f"{m.group(2)}-{mes:02d}" if mes else None


def ler_gabinetes(pagina: str) -> List[Dict[str, Any]]:
    saida = []
    for linha in re.findall(r"<tr[^>]*>(.*?)</tr>", pagina, re.S):
        link = re.search(r'href="(frame_verbadetalhe\.php[^"]*)"', linha)
        cel = _celulas(linha)
        if not link or len(cel) < 4:
            continue
        saida.append({
            "gabinete": cel[0],
            "deputado": re.sub(r"^GAB(INETE)?\.?\s*(DO\s+)?DEP(UTAD[OA])?\.?\s*", "", cel[0], flags=re.I).strip(),
            "referencia": _referencia(cel[1]),
            "assessores": int(cel[2]) if cel[2].isdigit() else None,
            "total": n.decimal(cel[3].replace("R$", "")),
            "detalhe": BASE + h.unescape(link.group(1)),
        })
    return saida


def ler_detalhe(pagina: str) -> List[Dict[str, Any]]:
    saida = []
    for linha in re.findall(r"<tr[^>]*>(.*?)</tr>", pagina, re.S):
        cel = _celulas(linha)
        if len(cel) < 6 or not cel[2]:
            continue
        saida.append({"nome": cel[2], "cargo": cel[3] or None, "lotacao": cel[4] or None, "valor": n.decimal(cel[5].replace("R$", ""))})
    return saida


def _candidatos() -> Dict[int, List[str]]:
    with sessao() as s:
        linhas = s.execute(select(Politico.codigo, Politico.nome, Politico.nome_civil).where(Politico.casa == CASA)).all()
    return {cod: [nome, civil] for cod, nome, civil in linhas}


def coletar_gabinetes(client: HttpClient) -> int:
    """Equipe de cada gabinete com o valor pago no último mês publicado."""
    from .tse import _titulo

    gabinetes = ler_gabinetes(client.get_bytes(GABINETES).decode("utf-8", "replace"))
    if len(gabinetes) < 20:
        raise RuntimeError(f"Verba de gabinete da Alepa com só {len(gabinetes)} gabinetes")
    candidatos = _candidatos()
    linhas: List[Dict[str, Any]] = []
    sem_dono = []
    for g in gabinetes:
        cod = casar_nome(g["deputado"], candidatos)
        if cod is None:
            sem_dono.append(g["deputado"])
            continue
        for p in ler_detalhe(client.get_bytes(g["detalhe"]).decode("utf-8", "replace")):
            linhas.append({
                "casa": CASA, "codigo_politico": cod, "nome": _titulo(p["nome"]), "cargo": p["cargo"],
                "funcao": None, "lotacao": p["lotacao"], "remuneracao": p["valor"], "remuneracao_ref": g["referencia"],
            })
    with sessao() as s:
        s.execute(delete(Assessor).where(Assessor.casa == CASA))
        if linhas:
            s.execute(insert(Assessor), linhas)
    logger.info("Alepa: %s pessoas em %s gabinetes; gabinetes sem deputado ligado: %s", len(linhas), len(gabinetes) - len(sem_dono), ", ".join(sem_dono) or "nenhum")
    return len(linhas)
