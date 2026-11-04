"""Funções de limpeza compartilhadas pelos coletores."""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    limpo = " ".join(str(valor).split())
    return limpo or None


def inteiro(valor: Any) -> Optional[int]:
    t = texto(valor)
    if t is None:
        return None
    try:
        return int(float(t))
    except ValueError:
        return None


def decimal(valor: Any) -> Optional[Decimal]:
    t = texto(valor)
    if t is None:
        return None
    if "," in t and "." in t:  # 1.234,56
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def data_hora(valor: Any) -> Optional[datetime]:
    t = texto(valor)
    if t is None:
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", ""))
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None


def data(valor: Any) -> Optional[date]:
    dh = data_hora(valor)
    return dh.date() if dh else None


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


# Valores observados nas duas casas. O original é sempre guardado também.
_VOTOS = {
    "sim": "sim",
    "nao": "nao",
    "abstencao": "abstencao",
    "abst": "abstencao",
    "obstrucao": "obstrucao",
    "obstr": "obstrucao",
    "artigo 17": "presidente",
    "art. 17": "presidente",
    "presidente (art. 51 ricd)": "presidente",
    "presidente": "presidente",
    "p-nrv": "presente_sem_voto",
    "presente": "presente_sem_voto",
    "ausente": "ausente",
    "ncom": "ausente",  # não compareceu
    "nao compareceu": "ausente",
    "nao votou": "ausente",
    "lp": "licenca",  # licença particular
    "ls": "licenca",  # licença saúde
    "lap": "licenca",
    "mis": "missao",  # missão oficial
    "aus": "ausente",
}


def voto(valor: Any) -> str:
    """Normaliza o voto para: sim, nao, abstencao, obstrucao, ausente,
    presidente, presente_sem_voto, licenca, missao ou outro."""
    t = texto(valor)
    if t is None:
        return "ausente"
    chave = _sem_acento(t).lower().strip()
    if chave in _VOTOS:
        return _VOTOS[chave]
    if chave.startswith("ausente") or chave.startswith("nao compareceu"):
        return "ausente"
    if chave.startswith("presidente"):
        return "presidente"
    if chave.startswith("lic"):
        return "licenca"
    return "outro"
