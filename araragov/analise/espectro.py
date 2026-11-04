"""Posição política a partir das votações, sem classificação manual.

Método (o mesmo usado em ciência política para o Congresso dos EUA e do
Brasil, como o NOMINATE e o Basômetro do Estadão):

1. Monta a matriz parlamentar x votação (Sim = +1, Não = -1, demais = vazio),
   só com votações disputadas (o lado perdedor teve pelo menos 10% dos votos).
2. A primeira componente principal (PCA) dessa matriz é o eixo que mais
   separa os parlamentares. Historicamente, no Brasil, esse eixo é o
   governo x oposição e a esquerda x direita.
3. O sentido do eixo é fixado pelos partidos de referência: quem fica do
   lado do PT, PSOL e PCdoB é "esquerda". É a única informação externa usada.
4. Cada votação disputada é classificada pelo lado de quem votou Sim:
   se a média dos que votaram Sim está mais à esquerda que a dos que votaram
   Não, então "Sim" é a posição mais à esquerda naquela votação. Votações em
   que os dois lados se misturam ficam "sem lado claro".
5. A posição do parlamentar é o percentual de votações classificadas em que
   ele votou com o lado da esquerda.

Nenhum rótulo extremista é usado: as faixas vão de esquerda a direita.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

PARTIDOS_ESQUERDA_REFERENCIA = {"PT", "PSOL", "PCDOB"}
MINORIA_MINIMA = 0.10  # votação disputada: perdedor com >= 10% dos votos
VOTOS_MINIMOS = 20  # parlamentar precisa de ao menos N votos para entrar no PCA
FORCA_MINIMA = 0.5  # separação mínima (em desvios-padrão) para dizer que há lado


@dataclass
class VotoSimples:
    votacao_id: str
    codigo_politico: int
    partido: Optional[str]
    voto: str  # sim | nao | ...


@dataclass
class LadoVotacao:
    lado_sim: Optional[str]  # "esquerda" | "direita" | None (sem lado claro)
    forca: float


@dataclass
class Resultado:
    # posição no eixo: negativo = esquerda; só informativo
    pontuacao: Dict[int, float] = field(default_factory=dict)
    votacoes: Dict[str, LadoVotacao] = field(default_factory=dict)
    # % das votações classificadas em que votou com o lado da esquerda
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


def calcular(votos: Iterable[VotoSimples]) -> Resultado:
    """Roda o método para uma casa legislativa."""
    por_votacao: Dict[str, Dict[int, int]] = defaultdict(dict)
    partido_de: Dict[int, str] = {}
    for v in votos:
        if v.voto in ("sim", "nao"):
            por_votacao[v.votacao_id][v.codigo_politico] = 1 if v.voto == "sim" else -1
            if v.partido:
                partido_de[v.codigo_politico] = _sigla(v.partido)

    disputadas = []
    for vid, vs in por_votacao.items():
        sims = sum(1 for x in vs.values() if x > 0)
        total = len(vs)
        if total and min(sims, total - sims) / total >= MINORIA_MINIMA:
            disputadas.append(vid)

    contagem: Dict[int, int] = defaultdict(int)
    for vid in disputadas:
        for cod in por_votacao[vid]:
            contagem[cod] += 1
    parlamentares = sorted(c for c, n in contagem.items() if n >= VOTOS_MINIMOS)
    resultado = Resultado()
    if len(parlamentares) < 3 or len(disputadas) < 3:
        return resultado

    linha = {c: i for i, c in enumerate(parlamentares)}
    m = np.full((len(parlamentares), len(disputadas)), np.nan)
    for j, vid in enumerate(disputadas):
        for cod, x in por_votacao[vid].items():
            if cod in linha:
                m[linha[cod], j] = x
    medias = np.nanmean(m, axis=0)
    centrada = np.where(np.isnan(m), 0.0, m - medias)
    u, s, _ = np.linalg.svd(centrada, full_matrices=False)
    escore = u[:, 0] * s[0]
    escore = escore / (escore.std() or 1.0)

    ref = [escore[linha[c]] for c in parlamentares if partido_de.get(c) in PARTIDOS_ESQUERDA_REFERENCIA]
    if ref and np.mean(ref) > 0:
        escore = -escore
    resultado.pontuacao = {c: float(escore[linha[c]]) for c in parlamentares}

    for vid in disputadas:
        sim = [resultado.pontuacao[c] for c, x in por_votacao[vid].items() if x > 0 and c in resultado.pontuacao]
        nao = [resultado.pontuacao[c] for c, x in por_votacao[vid].items() if x < 0 and c in resultado.pontuacao]
        if not sim or not nao:
            continue
        diferenca = float(np.mean(sim) - np.mean(nao))
        forca = abs(diferenca)
        lado = None
        if forca >= FORCA_MINIMA:
            lado = "esquerda" if diferenca < 0 else "direita"
        resultado.votacoes[vid] = LadoVotacao(lado, round(forca, 2))

    com_esquerda: Dict[int, List[bool]] = defaultdict(list)
    for vid, lado in resultado.votacoes.items():
        if lado.lado_sim is None:
            continue
        for cod, x in por_votacao[vid].items():
            votou_sim = x > 0
            com_esquerda[cod].append(votou_sim == (lado.lado_sim == "esquerda"))
    for cod, lista in com_esquerda.items():
        if len(lista) >= VOTOS_MINIMOS // 2:
            resultado.pct_esquerda[cod] = (round(100 * sum(lista) / len(lista), 1), len(lista))
    return resultado


def alinhamento_partidos(votos: Iterable[VotoSimples], minimo_comum: int = 10) -> Dict[int, List[dict]]:
    """Com quais partidos cada parlamentar mais vota junto.

    A posição de um partido numa votação é a da maioria dos seus membros que
    votaram Sim ou Não. O alinhamento é o % de votações em comum em que o
    parlamentar votou igual a essa maioria.
    """
    lista = [v for v in votos if v.voto in ("sim", "nao")]
    contagem: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])
    for v in lista:
        if v.partido:
            c = contagem[(v.votacao_id, _sigla(v.partido))]
            c[0 if v.voto == "sim" else 1] += 1
    posicao = {
        chave: ("sim" if s > n else "nao") for chave, (s, n) in contagem.items() if s != n
    }
    partidos_por_votacao: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for (vid, partido), pos in posicao.items():
        partidos_por_votacao[vid].append((partido, pos))

    acordos: Dict[int, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for v in lista:
        for partido, pos in partidos_por_votacao.get(v.votacao_id, []):
            a = acordos[v.codigo_politico][partido]
            a[1] += 1
            if v.voto == pos:
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
