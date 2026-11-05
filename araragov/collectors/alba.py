"""Assembleia Legislativa da Bahia (ALBA).

A página de verbas indenizatórias (https://www.al.ba.gov.br/transparencia/verbas-idenizatorias)
oferece a exportação em planilha por ano: /transparencia/verbas-idenizatorias-excel?ano=AAAA.
Cada linha traz processo, nota fiscal, data, deputado, categoria e valor. A
planilha não traz o fornecedor. O site não tem robots.txt.

O nome do deputado vem como nome de urna ("Alex da Piatã"); ligamos ao
deputado da lista do TSE pelo nome, só quando há um único candidato.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import select

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import casar_nome, data_excel, ler_xlsx, substituir_despesas

logger = logging.getLogger(__name__)

CASA = "al-ba"
PAGINA = "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias"
PLANILHA = PAGINA + "-excel?ano={ano}"


def _candidatos() -> Dict[int, List[str]]:
    with sessao() as s:
        linhas = s.execute(select(Politico.codigo, Politico.nome, Politico.nome_civil).where(Politico.casa == CASA)).all()
    return {cod: [nome, civil] for cod, nome, civil in linhas}


def linhas_verbas(conteudo: bytes, ano: int, candidatos: Dict[int, List[str]], limite: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    tabela = ler_xlsx(conteudo)
    colunas: Dict[str, int] = {}
    inicio = None
    for i, linha in enumerate(tabela):
        textos = [str(c).strip().upper() if c is not None else "" for c in linha]
        if any(t.startswith("DEPUTADO") for t in textos):
            for j, t in enumerate(textos):
                if t.startswith("DEPUTADO"):
                    colunas["deputado"] = j
                elif t.startswith("CATEGORIA"):
                    colunas["categoria"] = j
                elif t.startswith("VALOR"):
                    colunas["valor"] = j
                elif t == "DATA":
                    colunas["data"] = j
                elif "PROCESSO" in t:
                    colunas["processo"] = j
                elif t.startswith("N° NF") or t.startswith("Nº NF") or t == "NF":
                    colunas["nf"] = j
            inicio = i + 1
            break
    if inicio is None or not {"deputado", "valor"} <= colunas.keys():
        raise RuntimeError("Planilha da ALBA sem o cabeçalho esperado (DEPUTADO, VALOR)")

    def campo(linha: List[Any], nome: str) -> Any:
        j = colunas.get(nome)
        return linha[j] if j is not None and j < len(linha) else None

    repetidas: Counter = Counter()
    codigos: Dict[str, Any] = {}
    total = 0
    for linha in tabela[inicio:]:
        nome = n.texto(campo(linha, "deputado"))
        bruto = campo(linha, "valor")
        valor = n.decimal(bruto if not isinstance(bruto, float) else f"{bruto:.2f}")
        if nome is None or valor is None:
            continue
        if nome not in codigos:
            codigos[nome] = casar_nome(nome, candidatos)
        dia = data_excel(campo(linha, "data"))
        processo = n.texto(campo(linha, "processo")) or ""
        nf = n.texto(campo(linha, "nf")) or ""
        base = f"{processo}:{nf}:{nome}:{valor}"[:110]
        repetidas[base] += 1
        yield {
            "casa": CASA,
            "chave_fonte": f"{base}:{repetidas[base]}",
            "codigo_politico": codigos[nome],
            "nome_politico": nome,
            "ano": ano,
            "mes": dia.month if dia else 0,
            "categoria": " ".join((n.texto(campo(linha, "categoria")) or "Não informada").split()),
            "fornecedor": None,
            "cnpj_cpf": None,
            "data_documento": dia,
            "valor": valor,
            "url_documento": PAGINA,
        }
        total += 1
        if limite and total >= limite:
            break
    sem = sorted(c for c, cod in codigos.items() if cod is None)
    logger.info("ALBA %s: %s de %s nomes ligados a um deputado; sem perfil: %s", ano, len(codigos) - len(sem), len(codigos), ", ".join(sem) or "nenhum")


def coletar_despesas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    conteudo = client.get_bytes(PLANILHA.format(ano=ano))
    candidatos = _candidatos()
    with sessao() as s:
        total = substituir_despesas(s, CASA, ano, linhas_verbas(conteudo, ano, candidatos, limite))
    logger.info("ALBA: %s verbas indenizatórias gravadas em %s", total, ano)
    return total
