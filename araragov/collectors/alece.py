"""Assembleia Legislativa do Ceará (Alece).

Portal da transparência: https://transparencia.al.ce.gov.br/
A Alece publica a Verba de Desempenho Parlamentar como CSV por mês em
/despesas/verba-desempenho-parlamentar/csv?mes=MM&ano=AAAA (o mês precisa
de dois dígitos). Cada linha tem deputado, período, empenho, descrição,
CNPJ e nome do credor e valor. O robots.txt do portal não bloqueia nada.

O deputado vem como "DEP NOME DE URNA"; ligamos ao deputado da lista do TSE
pelo nome, e só quando há um único candidato.

A lista de deputados em exercício vem de https://www.al.ce.gov.br/deputados
(cartões com nome, partido e a marca "licenciado"); o nome completo vem da
página de cada deputado. O robots.txt do site só bloqueia o banco de imagens.

O portal também tem um CSV de votações nominais, mas ele só lista as
matérias e um PDF por votação, sem o voto de cada deputado em formato aberto.
"""

from __future__ import annotations

import logging
import html as h
import re
import zlib
from collections import Counter
from datetime import date
from typing import Any, Dict, Iterable, Iterator, List, Optional

from sqlalchemy import select

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import casar_nome, ler_csv, sincronizar_lista_oficial, substituir_despesas

logger = logging.getLogger(__name__)

CASA = "al-ce"
PORTAL = "https://transparencia.al.ce.gov.br"
PAGINA = PORTAL + "/despesas/verba-desempenho-parlamentar"
VERBA = PAGINA + "/csv?mes={mes:02d}&ano={ano}"
SITE = "https://www.al.ce.gov.br"
DEPUTADOS = SITE + "/deputados"


def ler_deputados(pagina: str) -> List[Dict[str, Any]]:
    """Cartões da página /deputados: em exercício e suplentes em exercício.
    Quem tem a marca "licenciado" fica de fora."""
    saida = []
    for classe, corpo, partido in re.findall(
        r'class="deputado_card([^"]*)"(.*?)deputado_card--partido[^>]*>([^<]*)<', pagina, re.S
    ):
        if "licenciado" in classe:
            continue
        m = re.search(r'/deputados/([a-z0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>', corpo)
        if not m:
            continue
        saida.append({
            # A Alece não publica um número; o código sai do endereço da página.
            "id": zlib.crc32(m.group(1).encode()) % 900_000,
            "slug": m.group(1),
            "nome": h.unescape(m.group(2)),
            "partido": h.unescape(partido).strip() or None,
        })
    return saida


def ler_nome_completo(pagina: str) -> Optional[str]:
    m = re.search(r"Nome Completo\s*(?:<[^>]+>\s*)*([^<]+?)\s*<", pagina)
    return h.unescape(m.group(1)).strip() if m else None


def coletar_deputados(client: HttpClient) -> int:
    oficiais = ler_deputados(client.get_bytes(DEPUTADOS).decode("utf-8", "replace"))
    if len(oficiais) < 35:
        raise RuntimeError(f"Lista da Alece com só {len(oficiais)} nomes; mantendo a do TSE")
    for o in oficiais:
        o["nome_civil"] = ler_nome_completo(client.get_bytes(f"{DEPUTADOS}/{o['slug']}").decode("utf-8", "replace"))
    with sessao() as s:
        r = sincronizar_lista_oficial(s, CASA, "CE", oficiais)
    logger.info("Alece: %s em exercício, %s suplentes novos, %s eleitos fora de exercício", r["em_exercicio"], r["suplentes"], r["fora"])
    return r["em_exercicio"]


def _sem_titulo(nome: str) -> str:
    return re.sub(r"^\s*DEP(UTAD[OA])?\.?\s+", "", nome, flags=re.I).strip()


def _candidatos() -> Dict[int, List[str]]:
    with sessao() as s:
        linhas = s.execute(select(Politico.codigo, Politico.nome, Politico.nome_civil).where(Politico.casa == CASA)).all()
    return {cod: [nome, civil] for cod, nome, civil in linhas}


def linhas_verba(conteudos: Iterable[bytes], ano: int, candidatos: Dict[int, List[str]], limite: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    repetidas: Counter = Counter()
    codigos: Dict[str, Any] = {}
    total = 0
    for conteudo in conteudos:
        texto = conteudo.decode("utf-8-sig", "replace")
        # A primeira linha do arquivo é ";;;" e o cabeçalho vem na segunda.
        i = texto.find("DEPUTADO;")
        if i < 0:
            continue
        for linha in ler_csv(texto[i:].encode("utf-8")):
            valor = n.decimal(linha.get("VALOR"))
            dep = n.texto(linha.get("DEPUTADO"))
            if valor is None or dep is None:
                continue
            nome = _sem_titulo(dep)
            if nome not in codigos:
                codigos[nome] = casar_nome(nome, candidatos)
            periodo = n.texto(linha.get("PERIODO")) or ""
            m = re.match(r"(\d{1,2})/(\d{4})", periodo)
            mes = int(m.group(1)) if m else 0
            empenho = n.texto(linha.get("EMPENHO")) or ""
            base = f"{nome}:{periodo}:{empenho}:{valor}"[:110]
            repetidas[base] += 1
            yield {
                "casa": CASA,
                "chave_fonte": f"{base}:{repetidas[base]}",
                "codigo_politico": codigos[nome],
                "nome_politico": nome,
                "ano": ano,
                "mes": mes,
                "categoria": n.texto(linha.get("DESCRICAO")) or "Verba de desempenho parlamentar",
                "fornecedor": n.texto(linha.get("CREDOR")),
                "cnpj_cpf": n.texto(linha.get("CNPJ")),
                "data_documento": date(ano, mes, 1) if 1 <= mes <= 12 else None,
                "valor": valor,
                "url_documento": PAGINA,
            }
            total += 1
            if limite and total >= limite:
                return
    sem = sorted(c for c, cod in codigos.items() if cod is None)
    logger.info("Alece %s: %s de %s nomes ligados a um deputado; sem perfil: %s", ano, len(codigos) - len(sem), len(codigos), ", ".join(sem) or "nenhum")


def coletar_despesas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    hoje = date.today()
    ultimo = hoje.month if ano == hoje.year else 12

    def arquivos() -> Iterator[bytes]:
        for mes in range(1, ultimo + 1):
            yield client.get_bytes(VERBA.format(mes=mes, ano=ano))

    candidatos = _candidatos()
    with sessao() as s:
        total = substituir_despesas(s, CASA, ano, linhas_verba(arquivos(), ano, candidatos, limite))
    logger.info("Alece: %s gastos da verba de desempenho gravados em %s", total, ano)
    return total
