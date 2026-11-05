"""Fase 6: emendas parlamentares federais que chegaram a cada município.

Fonte: o mesmo arquivo único do Portal da Transparência que a parte federal
usa (araragov/collectors/emendas.py). Para cada município, grava
`emendas.md` com quem recebeu o dinheiro ali (a prefeitura, uma entidade ou
uma empresa), de qual emenda e de qual autor.

A trilha vai da emenda até o primeiro favorecido. Quando o favorecido é a
própria prefeitura, o que ela pagou depois com aquele dinheiro só pode ser
seguido se a despesa municipal identificar a emenda; isso ainda não está nos
dados abertos que lemos, e o arquivo diz isso na tabela `sem-dados`.
Pessoas físicas que receberam aparecem somadas, sem nome nem CPF.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .. import normalizar as n
from ..collectors.emendas import ARQ_EMENDAS, ARQ_FAVORECIDOS, EMENDAS_URL
from . import md
from .eleitos import COLUNAS_SEM_DADOS, chave_nome, municipios_ibge
from .tcesp import _resumir, formatar_cnpj, so_digitos

logger = logging.getLogger(__name__)

PAGINA = "https://portaldatransparencia.gov.br/emendas"
TOP_LINHAS = 300
PESSOAS_FISICAS = "Pessoas físicas (somadas, sem nome)"

COLUNAS_RESUMO = ["ano", "emendas", "autores", "valor", "para_prefeitura", "para_outros"]
COLUNAS_AUTORES = ["autor", "tipo", "emendas", "valor"]
COLUNAS_RECEBIDO = ["ano", "emenda", "autor", "tipo", "funcao", "acao", "favorecido", "cnpj", "natureza", "valor"]


def _linhas(z: zipfile.ZipFile, nome: str) -> Iterator[Dict[str, str]]:
    with z.open(nome) as bruto:
        yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")


def ler_emendas(linhas: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, Optional[str]]]:
    """Código da emenda -> autor, tipo, função e ação (primeira linha)."""
    saida: Dict[str, Dict[str, Optional[str]]] = {}
    for r in linhas:
        codigo = (r.get("Código da Emenda") or "").strip()
        if not codigo or codigo.lower().startswith("sem") or codigo in saida:
            continue
        saida[codigo] = {
            "autor": n.texto(r.get("Nome do Autor da Emenda")),
            "tipo": n.texto(r.get("Tipo de Emenda")),
            "funcao": n.texto(r.get("Nome Função")),
            "acao": _resumir(r.get("Nome Ação"), 160) or None,
        }
    return saida


def eh_prefeitura(nome: Optional[str], natureza: Optional[str]) -> bool:
    t = chave_nome(nome or "")
    return "MUNICIPIO" in chave_nome(natureza or "") or t.startswith("MUNICIPIO DE ") or t.startswith("PREFEITURA ")


def agregar(linhas: Iterable[Dict[str, str]], emendas: Dict[str, Dict[str, Optional[str]]],
            ibge: Dict[Tuple[str, str], Tuple[int, str]], anos: Optional[Iterable[int]] = None
            ) -> Dict[int, Dict[Tuple, Dict[str, Any]]]:
    """IBGE -> (ano, emenda, favorecido) -> linha somada."""
    anos = set(anos) if anos else None
    por_mun: Dict[int, Dict[Tuple, Dict[str, Any]]] = defaultdict(dict)
    for r in linhas:
        ano_mes = (r.get("Ano/Mês") or "").strip()
        ano = int(ano_mes[:4]) if ano_mes[:4].isdigit() else None
        if ano is None or (anos and ano not in anos):
            continue
        uf = (r.get("UF Favorecido") or "").strip().upper()
        achado = ibge.get((uf, chave_nome(r.get("Município Favorecido") or "")))
        if not achado:
            continue
        codigo = (r.get("Código da Emenda") or "").strip()
        e = emendas.get(codigo, {})
        pf = "física" in (r.get("Tipo Favorecido") or "").lower()
        doc = so_digitos(r.get("Código do Favorecido"))
        if pf:
            nome, cnpj, natureza = PESSOAS_FISICAS, None, None
        else:
            nome = _resumir(r.get("Favorecido"), 120) or "Não informado"
            cnpj = formatar_cnpj(doc) if len(doc) == 14 else None
            natureza = n.texto(r.get("Natureza Jurídica"))
        chave = (ano, codigo, nome, cnpj)
        linha = por_mun[achado[0]].get(chave)
        if linha is None:
            linha = por_mun[achado[0]][chave] = {
                "ano": ano, "emenda": codigo, "autor": e.get("autor") or n.texto(r.get("Nome do Autor da Emenda")),
                "tipo": e.get("tipo") or n.texto(r.get("Tipo de Emenda")), "funcao": e.get("funcao"),
                "acao": e.get("acao"), "favorecido": nome, "cnpj": cnpj, "natureza": natureza,
                "valor": Decimal(0), "prefeitura": (not pf) and eh_prefeitura(nome, natureza),
            }
        linha["valor"] += n.decimal(r.get("Valor Recebido")) or Decimal(0)
    return por_mun


def documento(cod: int, mun: str, uf: str, linhas: Dict[Tuple, Dict[str, Any]], hoje: date) -> str:
    todas = [l for l in linhas.values() if l["valor"]]
    resumo = []
    for ano in sorted({l["ano"] for l in todas}, reverse=True):
        do_ano = [l for l in todas if l["ano"] == ano]
        pref = sum((l["valor"] for l in do_ano if l["prefeitura"]), Decimal(0))
        total = sum((l["valor"] for l in do_ano), Decimal(0))
        resumo.append({"ano": ano, "emendas": len({l["emenda"] for l in do_ano}),
                       "autores": len({l["autor"] for l in do_ano if l["autor"]}),
                       "valor": total, "para_prefeitura": pref, "para_outros": total - pref})
    autores: Dict[Tuple, Dict[str, Any]] = {}
    for l in todas:
        a = autores.setdefault((l["autor"], l["tipo"]), {"autor": l["autor"], "tipo": l["tipo"], "emendas": set(), "valor": Decimal(0)})
        a["emendas"].add(l["emenda"])
        a["valor"] += l["valor"]
    tab_autores = sorted(({**a, "emendas": len(a["emendas"])} for a in autores.values()), key=lambda a: -a["valor"])
    recebido = sorted(todas, key=lambda l: (-l["ano"], -l["valor"]))[:TOP_LINHAS]
    sem = [{
        "secao": "destino-final", "esfera": "municipal", "responsavel": "Prefeitura",
        "motivo": "Quando a emenda vai para a prefeitura, os dados abertos que lemos não dizem quais "
                  "empresas foram pagas com aquele dinheiro.",
        "obrigacao": "Rastreabilidade das emendas determinada pelo STF (ADPF 854)",
        "fonte_consultada": PAGINA, "consultado_em": hoje.isoformat(),
    }]
    meta = {"tipo": "municipio-emendas", "ibge": cod, "municipio": mun, "uf": uf, "atualizado": hoje,
            "fonte": EMENDAS_URL}
    return md.escrever(
        meta,
        {"resumo": resumo, "autores": tab_autores, "recebido": [{k: l[k] for k in COLUNAS_RECEBIDO} for l in recebido],
         "sem-dados": sem},
        colunas={"resumo": COLUNAS_RESUMO, "autores": COLUNAS_AUTORES, "recebido": COLUNAS_RECEBIDO,
                 "sem-dados": COLUNAS_SEM_DADOS},
        titulo=f"{mun} ({uf}), emendas parlamentares",
        textos={
            "resumo": "## Emendas recebidas por ano\n\nValores pagos pela União a quem está no município "
            "(prefeitura, entidades e empresas), pelo Portal da Transparência.",
            "autores": "## Quem mandou",
            "recebido": f"## Quem recebeu\n\nAs {TOP_LINHAS} maiores linhas (ano, emenda e favorecido). "
            "Receber emenda não é irregular; a lista mostra o caminho do dinheiro.",
            "sem-dados": "## O que ainda não há",
        },
    )


def gerar(client, saida: Path, anos: Optional[Iterable[int]] = None, ufs: Optional[Iterable[str]] = None,
          hoje: Optional[date] = None, pasta_tmp: Optional[Path] = None) -> int:
    hoje = hoje or date.today()
    pasta_tmp = pasta_tmp or saida.parent / "tmp"
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    arq = pasta_tmp / "emendas.zip"
    client.baixar_arquivo(EMENDAS_URL, arq)
    ibge = municipios_ibge()
    if ufs:
        ufs = {u.upper() for u in ufs}
        ibge = {k: v for k, v in ibge.items() if k[0] in ufs}
    try:
        with zipfile.ZipFile(arq) as z:
            info = ler_emendas(_linhas(z, ARQ_EMENDAS))
            por_mun = agregar(_linhas(z, ARQ_FAVORECIDOS), info, ibge, anos)
    finally:
        arq.unlink(missing_ok=True)
    uf_de = {cod: (uf, nome) for (uf, _), (cod, nome) in ibge.items()}
    total = 0
    for cod, linhas in por_mun.items():
        uf, nome = uf_de[cod]
        caminho = saida / "v1" / "municipios" / uf.lower() / str(cod) / "emendas.md"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(documento(cod, nome, uf, linhas, hoje), encoding="utf-8")
        total += 1
    logger.info("Emendas: %s municípios com favorecidos", total)
    return total
