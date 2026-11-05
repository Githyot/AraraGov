"""SINAPI pelo IBGE (SIDRA, tabela 2296): custo médio do m² construído por
estado e mês. Serve como índice de custo da construção de cada estado (para
levar um preço de um ano a outro, nível 3) e como referência genérica de
edificação (nível 1 do item "edificacao-media").

A API do SIDRA responde a partir do GitHub Actions; o pacote completo do
SINAPI na Caixa, não (HTTP 429).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from .. import normalizar as n
from .custos import Observacao
from .eleitos import municipios_ibge

logger = logging.getLogger(__name__)

# Variável 48: custo médio do m² em moeda corrente (R$).
URL = "https://apisidra.ibge.gov.br/values/t/2296/n3/all/v/48/p/all"
FONTE = "SINAPI/IBGE, custo médio do m² (SIDRA, tabela 2296)"
LINK = "https://sidra.ibge.gov.br/tabela/2296"


def _ufs_por_codigo() -> Dict[str, str]:
    """'41' -> 'PR', a partir dos códigos de município do IBGE."""
    return {str(cod)[:2]: uf for (uf, _), (cod, _) in municipios_ibge().items()}


def _colunas(cabecalho: Dict[str, str]) -> Tuple[str, str]:
    """Descobre quais chaves trazem o código da UF e o do mês."""
    uf = mes = None
    for chave, nome in cabecalho.items():
        nome = str(nome)
        if chave.endswith("C") and "Unidade da Federação" in nome:
            uf = chave
        elif chave.endswith("C") and nome.startswith("Mês"):
            mes = chave
    if not uf or not mes:
        raise ValueError(f"cabeçalho do SIDRA inesperado: {cabecalho}")
    return uf, mes


def custo_medio(client) -> Dict[Tuple[str, str], Decimal]:
    """(UF, 'AAAA-MM') -> custo médio do m² em R$."""
    dados = client.get_json(URL)
    if not dados:
        return {}
    col_uf, col_mes = _colunas(dados[0])
    ufs = _ufs_por_codigo()
    saida = {}
    for linha in dados[1:]:
        uf = ufs.get(str(linha.get(col_uf)))
        mes = str(linha.get(col_mes) or "")
        valor = n.decimal(linha.get("V"))
        if uf and len(mes) == 6 and valor:
            saida[(uf, f"{mes[:4]}-{mes[4:]}")] = valor
    logger.info("SIDRA 2296: %s valores mensais em %s estados", len(saida), len({u for u, _ in saida}))
    return saida


def indices_anuais(mensal: Dict[Tuple[str, str], Decimal]) -> Dict[Tuple[str, int], Decimal]:
    """Média do ano de cada estado; serve como índice de custo (nível 3)."""
    soma: Dict[Tuple[str, int], List[Decimal]] = defaultdict(list)
    for (uf, comp), v in mensal.items():
        soma[(uf, int(comp[:4]))].append(v)
    return {k: (sum(vs) / len(vs)).quantize(Decimal("0.01")) for k, vs in soma.items()}


def observacoes(mensal: Dict[Tuple[str, str], Decimal]) -> List[Observacao]:
    """Um preço por estado e ano (junho, ou o último mês do ano que houver)."""
    por_ano: Dict[Tuple[str, int], Tuple[str, Decimal]] = {}
    for (uf, comp), v in sorted(mensal.items()):
        chave = (uf, int(comp[:4]))
        if por_ano.get(chave, ("", 0))[0][5:] != "06":
            por_ano[chave] = (comp, v)  # fica junho; sem junho, o último mês
    return [
        Observacao("edificacao-media", uf, comp, v, "sinapi", FONTE, LINK)
        for (uf, _), (comp, v) in sorted(por_ano.items())
    ]
