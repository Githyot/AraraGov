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
            if valor is not None or campo == "fonte":
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


# --- Nomes -------------------------------------------------------------------

_TITULOS = {"dr", "dra", "doutor", "doutora", "sargento", "sgt", "cabo", "soldado", "coronel", "delegado",
            "delegada", "pastor", "pastora", "padre", "professor", "professora", "prof", "irmao", "irma"}
_LIGACOES = {"da", "de", "do", "das", "dos", "e"}


def _tokens(nome: str) -> List[str]:
    from ..normalizar import _sem_acento

    t = _sem_acento(nome or "").lower().replace(".", " ").replace("-", " ")
    return [p for p in t.split() if p and p not in _LIGACOES and p not in _TITULOS]


def casar_nome(nome: str, candidatos: Dict[int, Iterable[str]]) -> Any:
    """Acha o código do político cujo nome (de urna ou civil) corresponde a
    `nome`, como as assembleias escrevem nas planilhas ("Ana Paula da Silva
    (Paulinha)", "Dr Vicente Caropreso"). Só devolve quando há um único
    candidato; na dúvida devolve None, para nunca atribuir gasto à pessoa errada."""
    principal, _, apelido = (nome or "").partition("(")
    variantes = [v for v in (principal, apelido.rstrip(") ")) if v.strip()]
    nomes = {cod: [_tokens(x) for x in lista if x] for cod, lista in candidatos.items()}
    # 1) igual, 2) todas as palavras de um contidas no outro, 3) primeiro e último nome.
    regras = [
        lambda a, b: a == b,
        lambda a, b: len(a) >= 2 and len(b) >= 2 and (set(a) <= set(b) or set(b) <= set(a)),
        lambda a, b: len(a) >= 2 and len(b) >= 2 and a[0] == b[0] and a[-1] == b[-1],
    ]
    for regra in regras:
        achados = {
            cod
            for v in variantes
            for cod, lista in nomes.items()
            for c in lista
            if (t := _tokens(v)) and c and regra(t, c)
        }
        if len(achados) == 1:
            return achados.pop()
        if len(achados) > 1:
            return None
    return None
