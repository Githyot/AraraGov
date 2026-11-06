"""Contratos dos municípios do Rio de Janeiro pelo TCE-RJ (API de dados abertos).

`dados.tcerj.tc.br/api/v1/contratos_municipio?ano=&municipio=` devolve os
contratos de cada município fluminense (menos a capital, que é fiscalizada
pelo TCM-Rio) com o CNPJ da contratada, a modalidade, o objeto e os valores
empenhado, liquidado e pago. O CPF de pessoa física já vem mascarado.

Grava `{ano}-contratos.md` no mesmo formato da fase 4. O TCE-RJ não informa a
quantidade contratada, então as obras aparecem sem comparação de custo.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import publicados
from . import md
from .contratos import COLUNAS_CONTRATOS, classificar, comparar, documento
from .eleitos import COLUNAS_SEM_DADOS, chave_nome, municipios_ibge
from .tcesp import _resumir, formatar_cnpj, so_digitos

logger = logging.getLogger(__name__)

API = "https://dados.tcerj.tc.br/api/v1"
FONTE = "https://dados.tcerj.tc.br/"
CAPITAL = 3304557  # Rio de Janeiro: TCM-Rio
LIMITE = 20000
COLUNAS_RJ = COLUNAS_CONTRATOS + ["pago"]


def _decimal(v: Any) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    return Decimal(str(v)).quantize(Decimal("0.01"))


def agregar(linhas: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    m: Dict[str, Any] = {"contratos": [], "obras": [],
                         "diretas": defaultdict(lambda: {"n": 0, "valor": Decimal(0), "fund": set(), "empresa": ""})}
    vistos = set()
    for r in linhas:
        chave = (r.get("UnidadeGestora"), r.get("NumeroContrato"), r.get("AnoContrato"), r.get("CNPJCPFContratado"))
        if chave in vistos:
            continue
        vistos.add(chave)
        doc = so_digitos(r.get("CNPJCPFContratado"))
        pj = len(doc) == 14
        valor = _decimal(r.get("ValorContrato")) or Decimal(0)
        direta = bool(r.get("ProcessoDispensa")) and not r.get("ProcessoLicitatorio")
        modalidade = r.get("Modalidade") or ("Dispensa ou inexigibilidade" if direta else None)
        empresa = _resumir(r.get("Contratado"), 120) if pj else "Documento mascarado pelo TCE-RJ (nome omitido)"
        base = {
            "contrato": r.get("NumeroContrato"),
            "cnpj": formatar_cnpj(doc) if pj else None,
            "empresa": empresa,
            "orgao": f"Unidade gestora {r['UnidadeGestora']}" if r.get("UnidadeGestora") else None,
            "modalidade": modalidade,
            "objeto": _resumir(r.get("Objeto")),
            "valor": valor,
        }
        m["contratos"].append({**base, "assinatura": r.get("DataAssinaturaContrato"), "pago": _decimal(r.get("ValorPago"))})
        item = classificar(r.get("Objeto") or "")
        if item:
            m["obras"].append({**base, "item": item})
        if direta and pj:
            d = m["diretas"][doc]
            d["n"] += 1
            d["valor"] += valor
            d["empresa"] = empresa
            if r.get("ProcessoDispensa"):
                d["fund"].add("Dispensa ou inexigibilidade")
    return m


def _sem_dados(texto: str, hoje: date) -> str:
    doc = md.ler(texto)
    tabelas = dict(doc.tabelas)
    tabelas["sem-dados"] = [{
        "secao": "obras", "esfera": "municipal", "responsavel": "Prefeitura",
        "motivo": "O cadastro de contratos enviado ao TCE-RJ não traz a quantidade contratada, então o "
                  "valor por unidade não pode ser comparado com a referência.",
        "obrigacao": "Lei 14.133/2021, art. 92", "fonte_consultada": FONTE, "consultado_em": hoje.isoformat(),
    }]
    colunas = dict(doc.colunas)
    colunas["sem-dados"] = COLUNAS_SEM_DADOS
    titulo = next((l[2:] for l in texto.splitlines() if l.startswith("# ")), None)
    return md.escrever(doc.meta, tabelas, colunas=colunas, titulo=titulo, textos={
        "obras": "## Obras do ano\n\nContratos cujo objeto parece uma obra do catálogo de custos.",
        "contratos": "## Maiores contratos do ano\n\nValor do contrato e quanto já foi pago, segundo o TCE-RJ.",
        "contratacoes-diretas": "## Mesma empresa com várias contratações diretas",
        "sem-dados": "## O que ainda não há",
    })


def gerar(client, saida: Path, anos: Iterable[int], hoje: Optional[date] = None,
          limite_municipios: Optional[int] = None) -> int:
    from .custos import carregar_itens

    hoje = hoje or date.today()
    unidades_itens = {i.id: i.unidade for i in carregar_itens().values()}
    lista: List = sorted((cod, nome) for (uf, _), (cod, nome) in municipios_ibge().items() if uf == "RJ" and cod != CAPITAL)
    if limite_municipios:
        lista = lista[:limite_municipios]
    total = 0
    for ano in sorted(anos):
        reaproveitados = publicados.ano_ja_publicado(client, saida, "RJ", ano, hoje, "{ano}-contratos.md")
        if reaproveitados:
            total += reaproveitados
            continue
        for cod, nome in lista:
            try:
                dados = client.get_json(f"{API}/contratos_municipio",
                                        {"ano": ano, "municipio": chave_nome(nome), "limite": LIMITE})
            except Exception as exc:
                logger.warning("TCE-RJ %s %s: %s", nome, ano, exc)
                continue
            linhas = [r for r in (dados or {}).get("Contratos") or [] if int(r.get("AnoContrato") or 0) == ano]
            if not linhas:
                continue
            m = agregar(linhas)
            for o in m["obras"]:
                o.update({"quantidade": None, "unidade": None})
                o.update(comparar(o["item"], None, Decimal(0), o["valor"], {}, ano, unidades_itens))
            caminho = saida / "v1" / "municipios" / "rj" / str(cod) / f"{ano}-contratos.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            texto = documento(cod, nome, ano, m, hoje, uf="RJ", fonte=FONTE, colunas_contratos=COLUNAS_RJ)
            caminho.write_text(_sem_dados(texto, hoje), encoding="utf-8")
            total += 1
        logger.info("TCE-RJ %s: %s municípios com contratos", ano, total)
    return total
