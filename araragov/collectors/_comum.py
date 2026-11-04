"""Rotinas de gravação compartilhadas pelos coletores."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, Iterable, Iterator, List

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ..db import Despesa, Politico, Votacao, Voto

LOTE = 5000


def ler_csv(conteudo: bytes, separador: str = ";") -> Iterator[Dict[str, str]]:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    yield from csv.DictReader(io.StringIO(texto), delimiter=separador)


def gravar_politico(s: Session, dados: Dict[str, Any]) -> Politico:
    """Cria ou atualiza pelo par (casa, codigo)."""
    atual = s.execute(
        select(Politico).where(Politico.casa == dados["casa"], Politico.codigo == dados["codigo"])
    ).scalar_one_or_none()
    if atual is None:
        atual = Politico(**dados)
        s.add(atual)
    else:
        for campo, valor in dados.items():
            if valor is not None:
                setattr(atual, campo, valor)
    return atual


def gravar_votacao(s: Session, votacao: Dict[str, Any], votos: List[Dict[str, Any]]) -> None:
    """Grava a votação e substitui todos os votos dela (operação idempotente)."""
    s.merge(Votacao(**votacao))
    s.flush()
    s.execute(delete(Voto).where(Voto.votacao_id == votacao["id"]))
    vistos = set()
    unicos = []
    for v in votos:
        if v["codigo_politico"] in vistos:
            continue
        vistos.add(v["codigo_politico"])
        unicos.append({**v, "votacao_id": votacao["id"]})
    if unicos:
        s.execute(insert(Voto), unicos)


def substituir_despesas(s: Session, casa: str, ano: int, linhas: Iterable[Dict[str, Any]]) -> int:
    """Apaga as despesas do ano e grava as novas. A fonte republica o ano
    inteiro a cada atualização, então substituir é mais seguro que mesclar."""
    s.execute(delete(Despesa).where(Despesa.casa == casa, Despesa.ano == ano))
    total = 0
    lote: List[Dict[str, Any]] = []
    chaves = set()
    for linha in linhas:
        if linha["chave_fonte"] in chaves:
            continue
        chaves.add(linha["chave_fonte"])
        lote.append(linha)
        if len(lote) >= LOTE:
            s.execute(insert(Despesa), lote)
            total += len(lote)
            lote = []
    if lote:
        s.execute(insert(Despesa), lote)
        total += len(lote)
    return total
