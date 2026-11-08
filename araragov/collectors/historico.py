"""Histórico entre coletas.

O banco é recriado a cada coleta, mas alguns dados são caros de buscar de
novo (uma página por deputado e ano) e não mudam depois que o ano fecha. A
exportação publica esses dados em v1/historico/recursos.json; a coleta
seguinte começa lendo esse arquivo da API publicada e só busca o que falta.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import insert, select

from ..db import Assessor, AssessorAnterior, Beneficio, Despesa, RecursoMensal, sessao
from ..http import HttpClient

logger = logging.getLogger(__name__)

API_PUBLICA = os.environ.get("ARARAGOV_API_PUBLICA", "https://githyot.github.io/AraraGov/v1")
ARQUIVO = "historico/recursos.json"
CAMPOS_RECURSO = ("casa", "codigo_politico", "tipo", "ano", "mes", "valor")
CAMPOS_DESPESA = ("casa", "chave_fonte", "codigo_politico", "nome_politico", "ano", "mes", "categoria",
                  "fornecedor", "cnpj_cpf", "data_documento", "valor", "url_documento")
CAMPOS_GABINETE = ("casa", "codigo_politico", "nome", "cargo", "funcao", "desde", "ate")
# Despesas que só se conseguem com um pedido por deputado e mês (ALMG: 77 deputados x 12 meses
# por ano). As outras casas publicam o ano inteiro num arquivo só e são baixadas de novo.
DESPESAS_REAPROVEITADAS = ("al-mg",)
MES_FECHAMENTO = 4

# (casa, ano) cujas despesas vieram da coleta anterior; o coletor pula esses anos.
anos_carregados: set = set()


def ano_fechado(ano: int, hoje: Optional[date] = None) -> bool:
    """O ano não muda mais a partir de abril do ano seguinte."""
    hoje = hoje or date.today()
    return ano < hoje.year - 1 or (ano == hoje.year - 1 and hoje.month >= MES_FECHAMENTO)


def gabinetes(hoje: Optional[date] = None) -> Tuple[List[list], List[list]]:
    """Equipe atual e quem já saiu, para publicar e para a próxima coleta.

    Quem estava na equipe da coleta anterior e não está na de hoje sai com a
    data de hoje. Se a casa inteira veio vazia (fonte fora do ar), ninguém sai:
    a lista anterior continua valendo até a próxima coleta.
    """
    from .gabinete import _chave_nome

    hoje = hoje or date.today()
    with sessao() as s:
        atuais = [a for a in s.execute(select(Assessor).where(Assessor.codigo_politico.is_not(None))).scalars()]
        guardados = list(s.execute(select(AssessorAnterior).order_by(AssessorAnterior.id)).scalars())
    presentes = {(a.casa, a.codigo_politico, _chave_nome(a.nome)) for a in atuais}
    casas = {a.casa for a in atuais}
    linhas_atuais = [[a.casa, a.codigo_politico, a.nome, a.cargo, a.funcao, a.desde] for a in atuais]
    anteriores, vistos = [], set()
    for g in guardados:
        chave = (g.casa, g.codigo_politico, _chave_nome(g.nome))
        if chave in presentes:
            continue  # continua (ou voltou) na equipe
        if g.ate is None and g.casa not in casas:
            linhas_atuais.append([g.casa, g.codigo_politico, g.nome, g.cargo, g.funcao, g.desde])
            continue
        if (chave, g.desde) in vistos:
            continue
        vistos.add((chave, g.desde))
        anteriores.append([g.casa, g.codigo_politico, g.nome, g.cargo, g.funcao, g.desde, g.ate or hoje])
    return linhas_atuais, anteriores


def carregar(client: HttpClient, base: str = API_PUBLICA) -> int:
    dados = client.get_json(f"{base}/{ARQUIVO}")
    recursos = [
        {**dict(zip(CAMPOS_RECURSO, linha)), "valor": Decimal(str(linha[5])), "disponivel": None}
        for linha in dados.get("recursos") or []
    ]
    beneficios = [
        {**b, "valor_mensal": None, "valor_ano": None if b.get("valor_ano") is None else Decimal(str(b["valor_ano"]))}
        for b in dados.get("beneficios") or []
    ]
    despesas = []
    for linha in dados.get("despesas") or []:
        d = dict(zip(CAMPOS_DESPESA, linha))
        if d["casa"] not in DESPESAS_REAPROVEITADAS or not ano_fechado(d["ano"]):
            continue
        d["valor"] = Decimal(str(d["valor"]))
        d["data_documento"] = date.fromisoformat(d["data_documento"]) if d["data_documento"] else None
        despesas.append(d)
        anos_carregados.add((d["casa"], d["ano"]))
    gabinetes = dados.get("gabinetes") or {}
    pessoas = []
    for linha in (gabinetes.get("atuais") or []) + (gabinetes.get("anteriores") or []):
        g = dict(zip(CAMPOS_GABINETE, linha))
        g.setdefault("ate", None)
        for k in ("desde", "ate"):
            g[k] = date.fromisoformat(g[k]) if g[k] else None
        pessoas.append(g)
    with sessao() as s:
        if pessoas:
            s.execute(insert(AssessorAnterior), pessoas)
        if despesas:
            s.execute(insert(Despesa), despesas)
        if recursos:
            s.execute(insert(RecursoMensal), recursos)
        if beneficios:
            s.execute(insert(Beneficio), beneficios)
    logger.info("Histórico: %s valores mensais, %s benefícios, %s despesas e %s pessoas de gabinete da coleta anterior",
                len(recursos), len(beneficios), len(despesas), len(pessoas))
    return len(recursos)
