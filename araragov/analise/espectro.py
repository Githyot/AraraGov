"""Posição política a partir das votações, sem classificar leis à mão.

Método:

1. Partidos de referência: PT, PSOL e PCdoB (esquerda) e PL e NOVO (direita).
   É a única informação externa usada, e é consenso entre pesquisadores.
2. Uma votação é "ideológica" quando a maioria da esquerda de referência e a
   maioria da direita de referência votaram em lados opostos. Nela, o Sim
   recebe o lado de quem votou Sim (esquerda ou direita). Votações em que os
   dois blocos concordam ficam de fora: são consenso, não dizem nada sobre o
   lado de ninguém.
3. A posição de cada parlamentar é o percentual dessas votações em que ele
   votou com cada lado.

Por que não usar só o eixo principal das votações (PCA/NOMINATE)? No
Congresso brasileiro esse eixo costuma ser governo x oposição, e não
esquerda x direita: partidos de centro que apoiam o governo apareceriam
como "esquerda". Comparar com os dois blocos de referência evita isso.

Nenhum rótulo extremista é usado: as faixas vão de esquerda a direita.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

PARTIDOS_ESQUERDA_REFERENCIA = {"PT", "PSOL", "PCDOB"}
PARTIDOS_DIREITA_REFERENCIA = {"PL", "NOVO"}
MEMBROS_MINIMOS = 3  # cada bloco precisa de N votos (Sim/Não) na votação
COESAO_MINIMA = 0.6  # a maioria de cada bloco precisa ter ao menos 60%
VOTOS_MINIMOS = 10  # parlamentar precisa de N votações ideológicas para ter posição
# Para dizer como "o partido" votou sem contar a própria pessoa, o partido
# precisa de N outros membros votando Sim ou Não. Sem isso, num partido de
# um ou dois deputados o alinhamento com ele seria sempre ~100%.
OUTROS_MEMBROS_MINIMOS = 3


@dataclass
class VotoSimples:
    votacao_id: str
    codigo_politico: int
    partido: Optional[str]
    voto: str  # sim | nao | ...


@dataclass
class LadoVotacao:
    lado_sim: str  # "esquerda" | "direita"
    forca: float  # 0 a 1: quanto os dois blocos se separaram


@dataclass
class Resultado:
    votacoes: Dict[str, LadoVotacao] = field(default_factory=dict)
    # % das votações ideológicas em que votou com a esquerda, e quantas foram
    pct_esquerda: Dict[int, Tuple[float, int]] = field(default_factory=dict)


def faixa(pct_esquerda: float) -> str:
    if pct_esquerda >= 65:
        return "esquerda"
    if pct_esquerda >= 55:
        return "centro-esquerda"
    if pct_esquerda > 45:
        return "centro"
    if pct_esquerda > 35:
        return "centro-direita"
    return "direita"


def _sigla(p: Optional[str]) -> str:
    return (p or "").upper().replace(" ", "")


def _maioria(votos: List[bool]) -> Optional[Tuple[bool, float]]:
    """(votou_sim, fração) da maioria do bloco, se o bloco for coeso."""
    if len(votos) < MEMBROS_MINIMOS:
        return None
    frac_sim = sum(votos) / len(votos)
    if frac_sim >= COESAO_MINIMA:
        return True, frac_sim
    if 1 - frac_sim >= COESAO_MINIMA:
        return False, frac_sim
    return None


def calcular(votos: Iterable[VotoSimples], lados: Optional[Dict[str, LadoVotacao]] = None) -> Resultado:
    """Roda o método para uma casa legislativa.

    Com [lados], usa o lado já calculado de cada votação (sobre todo o período)
    e só recalcula o percentual de cada parlamentar nos [votos] dados, por
    exemplo os de um ano.
    """
    por_votacao: Dict[str, Dict[int, bool]] = defaultdict(dict)
    blocos: Dict[str, Dict[str, List[bool]]] = defaultdict(lambda: {"esquerda": [], "direita": []})
    for v in votos:
        if v.voto not in ("sim", "nao"):
            continue
        sim = v.voto == "sim"
        por_votacao[v.votacao_id][v.codigo_politico] = sim
        sigla = _sigla(v.partido)
        if sigla in PARTIDOS_ESQUERDA_REFERENCIA:
            blocos[v.votacao_id]["esquerda"].append(sim)
        elif sigla in PARTIDOS_DIREITA_REFERENCIA:
            blocos[v.votacao_id]["direita"].append(sim)

    resultado = Resultado()
    if lados is not None:
        resultado.votacoes = {vid: lado for vid, lado in lados.items() if vid in por_votacao}
    else:
        for vid, b in blocos.items():
            esq, dir_ = _maioria(b["esquerda"]), _maioria(b["direita"])
            if esq is None or dir_ is None or esq[0] == dir_[0]:
                continue
            lado = "esquerda" if esq[0] else "direita"
            resultado.votacoes[vid] = LadoVotacao(lado, round(abs(esq[1] - dir_[1]), 2))

    com_esquerda: Dict[int, List[bool]] = defaultdict(list)
    for vid, lado in resultado.votacoes.items():
        for cod, votou_sim in por_votacao[vid].items():
            com_esquerda[cod].append(votou_sim == (lado.lado_sim == "esquerda"))
    for cod, lista in com_esquerda.items():
        if len(lista) >= VOTOS_MINIMOS:
            resultado.pct_esquerda[cod] = (round(100 * sum(lista) / len(lista), 1), len(lista))
    return resultado


def alinhamento_partidos(votos: Iterable[VotoSimples], minimo_comum: int = 10) -> Dict[int, List[dict]]:
    """Com quais partidos cada parlamentar mais vota junto.

    A posição de um partido numa votação é a da maioria dos seus membros que
    votaram Sim ou Não, sem contar o próprio parlamentar. O alinhamento é o %
    de votações em comum em que ele votou igual a essa maioria. O partido de
    cada voto é o da época da votação.
    """
    lista = [v for v in votos if v.voto in ("sim", "nao")]
    contagem: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])
    for v in lista:
        if v.partido:
            c = contagem[(v.votacao_id, _sigla(v.partido))]
            c[0 if v.voto == "sim" else 1] += 1
    acordos: Dict[int, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    partidos_por_votacao: Dict[str, List[str]] = defaultdict(list)
    for vid, partido in contagem:
        partidos_por_votacao[vid].append(partido)
    for v in lista:
        meu = _sigla(v.partido) if v.partido else None
        for partido in partidos_por_votacao.get(v.votacao_id, []):
            s, n = contagem[(v.votacao_id, partido)]
            if partido == meu:  # tira o próprio voto da maioria do partido
                s, n = (s - 1, n) if v.voto == "sim" else (s, n - 1)
            if s + n < OUTROS_MEMBROS_MINIMOS or s == n:
                continue
            a = acordos[v.codigo_politico][partido]
            a[1] += 1
            if v.voto == ("sim" if s > n else "nao"):
                a[0] += 1
    saida: Dict[int, List[dict]] = {}
    for cod, por_partido in acordos.items():
        itens = [
            {"partido": p, "pct": round(100 * iguais / total, 1), "votacoes": total}
            for p, (iguais, total) in por_partido.items()
            if total >= minimo_comum
        ]
        saida[cod] = sorted(itens, key=lambda x: (-x["pct"], -x["votacoes"]))
    return saida
