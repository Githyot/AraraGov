"""Leitor e escritor do formato araragov-md/1 (docs/formato-md.md).

Um documento tem um cabeçalho plano (chave: valor) e tabelas identificadas
por um comentário `<!-- tabela: id -->`. Todo o resto é texto livre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

FORMATO = "araragov-md/1"

_ID_TABELA = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COLUNA = re.compile(r"^[a-z0-9_]+$")
_CHAVE = re.compile(r"^[a-z0-9_]+$")
_MARCA = re.compile(r"^<!--\s*tabela:\s*([^\s>]+)\s*-->$")
_SEPARADOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")


class ErroFormato(ValueError):
    """O texto não segue o formato araragov-md/1."""


@dataclass
class Documento:
    meta: Dict[str, str] = field(default_factory=dict)
    tabelas: Dict[str, List[Dict[str, Optional[str]]]] = field(default_factory=dict)
    colunas: Dict[str, List[str]] = field(default_factory=dict)


# --- escrita -----------------------------------------------------------------


def _celula(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, Decimal):
        texto = format(valor.normalize(), "f")
        return texto if "." not in texto else texto.rstrip("0").rstrip(".")
    if isinstance(valor, float):
        if valor != valor or valor in (float("inf"), float("-inf")):
            raise ErroFormato(f"número inválido: {valor}")
        return _celula(Decimal(repr(valor)))
    if isinstance(valor, date):
        return valor.isoformat()
    texto = " ".join(str(valor).split())
    return texto.replace("|", "\\|")


def _meta_valor(valor: Any) -> str:
    texto = _celula(valor).replace("\\|", "|")
    if texto.strip() in ("---",):
        raise ErroFormato("valor de cabeçalho não pode ser '---'")
    return texto


def escrever(
    meta: Mapping[str, Any],
    tabelas: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    colunas: Optional[Mapping[str, Sequence[str]]] = None,
    titulo: Optional[str] = None,
    textos: Optional[Mapping[str, str]] = None,
) -> str:
    """Gera o texto do documento.

    `colunas[id]` fixa a ordem das colunas de uma tabela; sem ela, a ordem é a
    das chaves na primeira aparição. `textos[id]` é um parágrafo (e um título
    `##`, se começar por ele) escrito antes da tabela, só para quem lê.
    """
    if "tipo" not in meta:
        raise ErroFormato("cabeçalho sem 'tipo'")
    linhas = ["---", f"formato: {FORMATO}"]
    for chave, valor in meta.items():
        if chave == "formato":
            continue
        if not _CHAVE.match(chave):
            raise ErroFormato(f"chave de cabeçalho inválida: {chave!r}")
        linhas.append(f"{chave}: {_meta_valor(valor)}")
    linhas.append("---")
    if titulo:
        linhas += ["", f"# {' '.join(titulo.split())}"]
    for id_tabela, registros in tabelas.items():
        if not _ID_TABELA.match(id_tabela):
            raise ErroFormato(f"id de tabela inválido: {id_tabela!r}")
        nomes = list(colunas[id_tabela]) if colunas and id_tabela in colunas else _ordem(registros)
        for nome in nomes:
            if not _COLUNA.match(nome):
                raise ErroFormato(f"coluna inválida em {id_tabela}: {nome!r}")
        if not nomes:
            raise ErroFormato(f"tabela {id_tabela} sem colunas")
        linhas.append("")
        if textos and id_tabela in textos:
            linhas += [textos[id_tabela].strip(), ""]
        linhas.append(f"<!-- tabela: {id_tabela} -->")
        linhas.append("| " + " | ".join(nomes) + " |")
        linhas.append("|" + "---|" * len(nomes))
        for registro in registros:
            extras = set(registro) - set(nomes)
            if extras:
                raise ErroFormato(f"tabela {id_tabela}: colunas não declaradas {sorted(extras)}")
            linhas.append("| " + " | ".join(_celula(registro.get(n)) for n in nomes) + " |")
    return "\n".join(linhas) + "\n"


def _ordem(registros: Iterable[Mapping[str, Any]]) -> List[str]:
    nomes: List[str] = []
    for registro in registros:
        for chave in registro:
            if chave not in nomes:
                nomes.append(chave)
    return nomes


# --- leitura -----------------------------------------------------------------


def _dividir(linha: str) -> List[str]:
    corpo = linha.strip()
    if not (corpo.startswith("|") and corpo.endswith("|")) or len(corpo) < 2:
        raise ErroFormato(f"linha de tabela inválida: {linha!r}")
    corpo = corpo[1:-1]
    celulas, atual, i = [], [], 0
    while i < len(corpo):
        c = corpo[i]
        if c == "\\" and i + 1 < len(corpo) and corpo[i + 1] == "|":
            atual.append("|")
            i += 2
            continue
        if c == "|":
            celulas.append("".join(atual).strip())
            atual = []
        else:
            atual.append(c)
        i += 1
    celulas.append("".join(atual).strip())
    return celulas


def ler(texto: str) -> Documento:
    linhas = texto.replace("\r\n", "\n").split("\n")
    doc = Documento()
    if not linhas or linhas[0].strip() != "---":
        raise ErroFormato("o arquivo deve começar com '---'")
    i = 1
    while True:
        if i >= len(linhas):
            raise ErroFormato("cabeçalho sem '---' de fechamento")
        linha = linhas[i].strip()
        i += 1
        if linha == "---":
            break
        if not linha:
            continue
        chave, sep, valor = linha.partition(":")
        if not sep or not _CHAVE.match(chave.strip()):
            raise ErroFormato(f"linha de cabeçalho inválida: {linha!r}")
        doc.meta[chave.strip()] = valor.strip()
    if doc.meta.get("formato") != FORMATO:
        raise ErroFormato(f"formato não suportado: {doc.meta.get('formato')!r}")
    if "tipo" not in doc.meta:
        raise ErroFormato("cabeçalho sem 'tipo'")

    while i < len(linhas):
        marca = _MARCA.match(linhas[i].strip())
        i += 1
        if not marca:
            continue
        id_tabela = marca.group(1)
        if not _ID_TABELA.match(id_tabela) or id_tabela in doc.tabelas:
            raise ErroFormato(f"id de tabela inválido ou repetido: {id_tabela!r}")
        if i + 1 >= len(linhas):
            raise ErroFormato(f"tabela {id_tabela} incompleta")
        nomes = _dividir(linhas[i])
        if not all(_COLUNA.match(n) for n in nomes):
            raise ErroFormato(f"tabela {id_tabela}: nomes de coluna inválidos {nomes}")
        if not _SEPARADOR.match(linhas[i + 1].strip().replace(" ", "")):
            raise ErroFormato(f"tabela {id_tabela}: falta a linha |---|")
        i += 2
        registros: List[Dict[str, Optional[str]]] = []
        while i < len(linhas) and linhas[i].strip().startswith("|"):
            celulas = _dividir(linhas[i])
            if len(celulas) != len(nomes):
                raise ErroFormato(
                    f"tabela {id_tabela}, linha {i + 1}: {len(celulas)} células, esperado {len(nomes)}"
                )
            registros.append({n: (c if c != "" else None) for n, c in zip(nomes, celulas)})
            i += 1
        doc.tabelas[id_tabela] = registros
        doc.colunas[id_tabela] = nomes
    return doc


def numero(valor: Optional[str]) -> Optional[Decimal]:
    """Converte uma célula numérica (ponto decimal); vazio vira None."""
    if valor is None:
        return None
    try:
        return Decimal(valor)
    except Exception as erro:  # decimal.InvalidOperation
        raise ErroFormato(f"número inválido: {valor!r}") from erro
