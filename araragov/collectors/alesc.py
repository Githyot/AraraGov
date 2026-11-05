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
from typing import Any, Dict, Iterator, List, Optional, Tuple

from sqlalchemy import select

from sqlalchemy import delete, insert

from ..db import Assessor, Politico, sessao
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


# --- Gabinetes ----------------------------------------------------------------

SERVIDORES = PORTAL + "/servidores"


def ler_setores_gabinete(html: str) -> Dict[int, str]:
    """Opções do filtro de lotação que são gabinete de deputado ("GAB DEP X")."""
    import re

    return {
        int(v): " ".join(nome.split())[len("GAB DEP "):]
        for v, nome in re.findall(r'<option value="(\d+)">\s*(GAB DEP [^<]+?)\s*</option>', html + "</option>")
    }


def ler_servidores(html: str) -> Tuple[List[Dict[str, str]], int]:
    """Linhas (nome, vínculo, lotação) e o total de páginas da listagem."""
    import re

    linhas = [
        {"nome": " ".join(nome.split()), "vinculo": " ".join(vinc.split()), "lotacao": " ".join(lot.split())}
        for nome, vinc, lot in re.findall(
            r'<td class="fw-semibold">([^<]+)</td>\s*<td>([^<]*)</td>\s*<td class="small">([^<]*)</td>', html
        )
    ]
    m = re.search(r"P[aá]gina \d+ de (\d+)", html)
    return linhas, int(m.group(1)) if m else 1


def coletar_gabinetes(client: HttpClient) -> int:
    """Quem está lotado no gabinete de cada deputado (nome e vínculo).

    A Alesc mostra a remuneração só na tela de contracheque, que o robots.txt
    pede para não acessar; por isso a equipe vem sem salário."""
    from .tse import _titulo

    inicial = client.get_bytes(SERVIDORES).decode("utf-8", "replace")
    setores = ler_setores_gabinete(inicial)
    if not setores:
        raise RuntimeError("Filtro de gabinetes não encontrado na página de servidores da Alesc")
    candidatos = _candidatos()
    linhas: List[Dict[str, Any]] = []
    sem_dono = []
    for setor, nome_dep in setores.items():
        cod = casar_nome(nome_dep, candidatos)
        if cod is None:
            sem_dono.append(nome_dep)
            continue
        pagina, total = 1, 1
        while pagina <= total:
            html = client.get_bytes(f"{SERVIDORES}?setor_id={setor}&page={pagina}").decode("utf-8", "replace")
            pessoas, total = ler_servidores(html)
            for pessoa in pessoas:
                linhas.append({
                    "casa": CASA, "codigo_politico": cod, "nome": _titulo(pessoa["nome"]),
                    "cargo": pessoa["vinculo"] or None, "funcao": None, "lotacao": pessoa["lotacao"] or None,
                })
            pagina += 1
    with sessao() as s:
        s.execute(delete(Assessor).where(Assessor.casa == CASA))
        if linhas:
            s.execute(insert(Assessor), linhas)
    logger.info("Alesc: %s pessoas em %s gabinetes; gabinetes sem deputado ligado: %s", len(linhas), len(setores) - len(sem_dono), ", ".join(sem_dono) or "nenhum")
    return len(linhas)
