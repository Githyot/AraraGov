"""Assembleia Legislativa de Santa Catarina (Alesc).

Portal da transparência: https://transparencia.alesc.sc.gov.br/
A Alesc publica um CSV por ano com todos os gastos dos gabinetes
parlamentares (diárias, passagens, telefone, aluguel do escritório de apoio,
combustível...), em /gabinetes-parlamentares/csv/{ano}, desde 2011. O
robots.txt do portal permite esses arquivos (só bloqueia as telas internas
de contracheque).

Cada linha traz o nome do deputado como a Alesc escreve ("Ana Paula da
Silva (Paulinha)"). Ligamos ao deputado da lista do TSE pelo nome, e só
quando há um único candidato; o resto fica com o nome, sem perfil.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import select

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import casar_nome, ler_csv, sincronizar_lista_oficial, substituir_despesas

logger = logging.getLogger(__name__)

CASA = "al-sc"
PORTAL = "https://transparencia.alesc.sc.gov.br"
GABINETES = PORTAL + "/gabinetes-parlamentares/csv/{ano}"
PAGINA = PORTAL + "/gabinetes-parlamentares"
DEPUTADOS = PORTAL + "/deputados"


def ler_deputados(html: str) -> List[Dict[str, Any]]:
    """Linhas da tabela de /deputados: nome (como a Alesc grava, às vezes o
    civil, às vezes o de urna) e a matrícula que aparece no link de remuneração.
    Só lemos a tabela; a tela de contracheque não é acessada (robots.txt)."""
    import re

    vistos = set()
    saida = []
    for nome, mat in re.findall(r'fw-semibold">\s*([^<]+?)\s*</td>.*?/deputados/contracheque/(\d+)', html, re.S):
        if mat in vistos:
            continue
        vistos.add(mat)
        saida.append({"id": int(mat), "nome": nome.strip()})
    return saida


def coletar_deputados(client: HttpClient) -> int:
    """Cruza a lista de deputados da Alesc com os eleitos do TSE: suplentes
    em exercício ganham perfil e quem se afastou fica fora de exercício."""
    oficiais = ler_deputados(client.get_bytes(DEPUTADOS).decode("utf-8", "replace"))
    if len(oficiais) < 30:
        raise RuntimeError(f"Lista da Alesc com só {len(oficiais)} nomes; mantendo a do TSE")
    with sessao() as s:
        r = sincronizar_lista_oficial(s, CASA, "SC", oficiais)
    logger.info("Alesc: %s em exercício, %s suplentes novos, %s eleitos fora de exercício", r["em_exercicio"], r["suplentes"], r["fora"])
    return r["em_exercicio"]


def _candidatos() -> Dict[int, List[str]]:
    with sessao() as s:
        linhas = s.execute(select(Politico.codigo, Politico.nome, Politico.nome_civil).where(Politico.casa == CASA)).all()
    return {cod: [nome, civil] for cod, nome, civil in linhas}


def linhas_gabinetes(conteudo: bytes, ano: int, candidatos: Dict[int, List[str]], limite: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    repetidas: Counter = Counter()
    codigos: Dict[str, Any] = {}
    total = 0
    for linha in ler_csv(conteudo):
        valor = n.decimal(linha.get("Valor"))
        data = n.data(linha.get("Data de Referência"))
        conta = n.texto(linha.get("Conta"))
        if valor is None or conta is None:
            continue
        if conta not in codigos:
            codigos[conta] = casar_nome(conta, candidatos)
        verba = n.texto(linha.get("Verba")) or ""
        descricao = n.texto(linha.get("Descrição")) or verba
        favorecido = n.texto(linha.get("Favorecido")) or n.texto(linha.get("Trecho"))
        mes = data.month if data else 0
        base = f"{conta}:{data}:{descricao[:40]}:{favorecido or ''}:{valor}"[:110]
        repetidas[base] += 1
        yield {
            "casa": CASA,
            "chave_fonte": f"{base}:{repetidas[base]}",
            "codigo_politico": codigos[conta],
            "nome_politico": conta,
            "ano": ano,
            "mes": mes,
            "categoria": descricao,
            "fornecedor": favorecido,
            "cnpj_cpf": None,
            "data_documento": data,
            "valor": valor,
            "url_documento": PAGINA,
        }
        total += 1
        if limite and total >= limite:
            break
    sem = sorted(c for c, cod in codigos.items() if cod is None)
    logger.info("Alesc %s: %s de %s nomes ligados a um deputado; sem perfil: %s", ano, len(codigos) - len(sem), len(codigos), ", ".join(sem) or "nenhum")


def coletar_despesas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    conteudo = client.get_bytes(GABINETES.format(ano=ano))
    candidatos = _candidatos()
    with sessao() as s:
        total = substituir_despesas(s, CASA, ano, linhas_gabinetes(conteudo, ano, candidatos, limite))
    logger.info("Alesc: %s gastos de gabinete gravados em %s", total, ano)
    return total
