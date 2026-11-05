"""Pagamentos e contratos dos municípios de SP, pelo TCE-SP (fase 4, piloto).

O Tribunal de Contas do Estado de São Paulo publica, para os 644 municípios
do estado (menos a capital, que tem tribunal próprio), todos os empenhos,
liquidações e pagamentos com o favorecido, e os contratos ("ajustes"):

    https://transparencia.tce.sp.gov.br/conjunto-de-dados

O arquivo de despesas de um ano tem ~15 GB (CSV, latin-1) dentro de um zip
de ~2 GB. Ele é lido em fluxo, sem descompactar no disco, e resumido por
município em `v1/municipios/sp/{ibge}/{ano}-pagamentos.md`:

- `favorecidos`: empresas (CNPJ) que mais receberam no ano.
- `areas-favorecidos`: em cada área (função/subfunção), quem mais recebeu.
- `obras`: empenhos do elemento "obras e instalações", com o histórico.

Pagamentos a pessoas físicas (CPF) entram só como total e quantidade, sem
nome nem CPF (LGPD). Folha de pagamento, encargos e dívida (elementos 31,
32 e 46) ficam fora do ranking de fornecedores.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from . import md

logger = logging.getLogger(__name__)

BASE = "https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados"
DESPESAS_URL = BASE + "/despesas-{ano}.zip"
FONTE = "https://transparencia.tce.sp.gov.br/conjunto-de-dados"
PAGO = "valor pago"
# Elementos fora do ranking de fornecedores: pessoal, encargos, dívida.
FORA_DO_RANKING = ("31", "32", "46")
ELEMENTO_OBRAS = "449051"

TOP_FAVORECIDOS = 50
TOP_POR_AREA = 10
TOP_OBRAS = 100

COLUNAS_FAVORECIDOS = ["posicao", "cnpj", "favorecido", "pago", "pagamentos", "areas"]
COLUNAS_AREAS = ["funcao", "subfuncao", "posicao", "cnpj", "favorecido", "pago"]
COLUNAS_OBRAS = ["orgao", "empenho", "cnpj", "favorecido", "pago", "acao", "historico"]
COLUNAS_RESUMO = ["grupo", "pago", "pagamentos"]


def valor(texto: Optional[str]) -> Decimal:
    """'1.234,56' -> Decimal('1234.56')."""
    t = (texto or "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(t) if t else Decimal(0)
    except InvalidOperation:
        return Decimal(0)


def so_digitos(texto: Optional[str]) -> str:
    return re.sub(r"\D", "", texto or "")


def formatar_cnpj(d: str) -> str:
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else d


# Sem \b: no nome de MEI o CPF vem colado ao nome ("FULANA12345678901").
_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")


def _resumir(texto: Optional[str], limite: int = 220) -> str:
    """Encurta e tira CPFs (o nome de um MEI costuma trazer o CPF do dono)."""
    t = " ".join(_CPF.sub("", texto or "").split())
    return t if len(t) <= limite else t[: limite - 1].rstrip() + "…"


@dataclass
class Favorecido:
    nome: str
    pago: Decimal = Decimal(0)
    pagamentos: int = 0
    areas: Set[str] = field(default_factory=set)


@dataclass
class Municipio:
    nome: str = ""
    favorecidos: Dict[str, Favorecido] = field(default_factory=dict)
    por_area: Dict[Tuple[str, str], Dict[str, Decimal]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(Decimal)))
    nomes: Dict[str, str] = field(default_factory=dict)
    obras: Dict[Tuple[str, str], Dict[str, Any]] = field(default_factory=dict)
    pf_pago: Decimal = Decimal(0)
    pf_pagamentos: int = 0
    pf_pessoas: Set[str] = field(default_factory=set)
    fora_pago: Decimal = Decimal(0)
    fora_pagamentos: int = 0


def linhas_despesas(conteudo_zip: Path) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(conteudo_zip) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".csv"):
                with z.open(nome) as f:
                    yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def agregar(linhas: Iterable[Dict[str, str]], limite: Optional[int] = None) -> Dict[int, Municipio]:
    municipios: Dict[int, Municipio] = defaultdict(Municipio)
    for i, l in enumerate(linhas):
        if limite is not None and i >= limite:
            logger.info("TCE-SP: parado em %s linhas (limite)", i)
            break
        if (l.get("tp_despesa") or "").strip().lower() != PAGO:
            continue
        try:
            ibge = int(l.get("codigo_municipio_ibge") or 0)
        except ValueError:
            continue
        if not ibge:
            continue
        m = municipios[ibge]
        m.nome = m.nome or (l.get("ds_municipio") or "").strip()
        v = valor(l.get("vl_despesa"))
        elemento = so_digitos((l.get("ds_elemento") or "").split("-")[0])
        tipo_id = (l.get("tp_identificador_despesa") or "").upper()
        ident = so_digitos(l.get("nr_identificador_despesa"))
        if elemento.startswith(FORA_DO_RANKING):
            m.fora_pago += v
            m.fora_pagamentos += 1
            continue
        if "CPF" in tipo_id or len(ident) == 11:
            # Pessoa física: só total, quantidade e número de pessoas (sem guardar o CPF).
            m.pf_pago += v
            m.pf_pagamentos += 1
            m.pf_pessoas.add(hashlib.sha1(ident.encode()).hexdigest()[:12])
            continue
        if len(ident) != 14:
            continue
        nome = _resumir(l.get("ds_despesa"), 120)
        f = m.favorecidos.setdefault(ident, Favorecido(nome))
        f.pago += v
        f.pagamentos += 1
        funcao = (l.get("ds_funcao_governo") or "").strip().title()
        subfuncao = (l.get("ds_subfuncao_governo") or "").strip().title()
        f.areas.add(funcao)
        m.por_area[(funcao, subfuncao)][ident] += v
        m.nomes[ident] = nome
        if elemento.startswith(ELEMENTO_OBRAS):
            chave = ((l.get("ds_orgao") or "").strip(), (l.get("nr_empenho") or "").strip())
            o = m.obras.setdefault(chave, {"cnpj": ident, "favorecido": nome, "pago": Decimal(0),
                                           "acao": _resumir(l.get("ds_acao"), 120),
                                           "historico": _resumir(l.get("historico_despesa"))})
            o["pago"] += v
    return municipios


def _governo(saida: Path, ibge: int, ano: int) -> Optional[str]:
    """Prefeito do ano, a partir do resumo.md gerado na fase 1."""
    caminho = saida / "v1" / "municipios" / "sp" / str(ibge) / "resumo.md"
    if not caminho.exists():
        return None
    try:
        doc = md.ler(caminho.read_text(encoding="utf-8"))
    except md.ErroFormato:
        return None
    for r in doc.tabelas.get("mandatos", []):
        if r.get("cargo") == "Prefeito" and int(r["inicio"]) <= ano <= int(r["fim"]):
            return f"{r['nome']} ({r['partido']}), mandato {r['inicio']}-{r['fim']}"
    return None


def documento(ibge: int, ano: int, m: Municipio, hoje: date, governo: Optional[str]) -> str:
    ranking = sorted(m.favorecidos.items(), key=lambda kv: kv[1].pago, reverse=True)[:TOP_FAVORECIDOS]
    total_pj = sum((f.pago for f in m.favorecidos.values()), Decimal(0))
    favorecidos = [
        {"posicao": i, "cnpj": formatar_cnpj(c), "favorecido": f.nome, "pago": f.pago,
         "pagamentos": f.pagamentos, "areas": ", ".join(sorted(a for a in f.areas if a))}
        for i, (c, f) in enumerate(ranking, 1)
    ]
    areas = []
    for (funcao, subfuncao), por_cnpj in sorted(m.por_area.items()):
        for i, (c, v) in enumerate(sorted(por_cnpj.items(), key=lambda kv: kv[1], reverse=True)[:TOP_POR_AREA], 1):
            areas.append({"funcao": funcao, "subfuncao": subfuncao, "posicao": i,
                          "cnpj": formatar_cnpj(c), "favorecido": m.nomes.get(c), "pago": v})
    obras = [
        {"orgao": k[0], "empenho": k[1], "cnpj": formatar_cnpj(o["cnpj"]), "favorecido": o["favorecido"],
         "pago": o["pago"], "acao": o["acao"], "historico": o["historico"]}
        for k, o in sorted(m.obras.items(), key=lambda kv: kv[1]["pago"], reverse=True)[:TOP_OBRAS]
    ]
    resumo = [
        {"grupo": "Empresas e entidades (CNPJ)", "pago": total_pj, "pagamentos": sum(f.pagamentos for f in m.favorecidos.values())},
        {"grupo": f"Pessoas físicas ({len(m.pf_pessoas)} pessoas, sem nome nem CPF)", "pago": m.pf_pago, "pagamentos": m.pf_pagamentos},
        {"grupo": "Pessoal, encargos e dívida (fora do ranking)", "pago": m.fora_pago, "pagamentos": m.fora_pagamentos},
    ]
    meta = {"tipo": "municipio-pagamentos", "ibge": ibge, "municipio": m.nome.title(), "uf": "SP", "ano": ano,
            "governo": governo, "atualizado": hoje, "fonte": FONTE}
    return md.escrever(
        {k: v for k, v in meta.items() if v is not None},
        {"resumo": resumo, "favorecidos": favorecidos, "areas-favorecidos": areas, "obras": obras},
        colunas={"resumo": COLUNAS_RESUMO, "favorecidos": COLUNAS_FAVORECIDOS,
                 "areas-favorecidos": COLUNAS_AREAS, "obras": COLUNAS_OBRAS},
        titulo=f"{m.nome.title()} (SP), pagamentos de {ano}",
        textos={
            "resumo": "## Pagamentos do ano\n\nValores pagos (não só empenhados), segundo o TCE-SP. "
            "Receber muito do município não é irregular: o ranking mostra para onde foi o dinheiro.",
            "favorecidos": "## Empresas que mais receberam",
            "areas-favorecidos": "## Quem recebeu em cada área",
            "obras": "## Obras pagas no ano\n\nEmpenhos do elemento \"obras e instalações\", com o histórico "
            "escrito pela prefeitura.",
        },
    )


def gerar(client, saida: Path, anos: Iterable[int], limite_linhas: Optional[int] = None,
          hoje: Optional[date] = None, pasta_tmp: Optional[Path] = None) -> int:
    hoje = hoje or date.today()
    pasta_tmp = pasta_tmp or saida.parent / "tmp"
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    total = 0
    for ano in sorted(anos):
        arquivo = pasta_tmp / f"tcesp-despesas-{ano}.zip"
        baixar(client, DESPESAS_URL.format(ano=ano), arquivo)
        municipios = agregar(linhas_despesas(arquivo), limite_linhas)
        for ibge, m in municipios.items():
            caminho = saida / "v1" / "municipios" / "sp" / str(ibge) / f"{ano}-pagamentos.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(documento(ibge, ano, m, hoje, _governo(saida, ibge, ano)), encoding="utf-8")
        arquivo.unlink(missing_ok=True)
        logger.info("TCE-SP %s: %s municípios", ano, len(municipios))
        total += len(municipios)
    return total


def baixar(client, url: str, destino: Path) -> None:
    """Baixa em partes para o disco (o zip de um ano tem ~2 GB)."""
    if hasattr(client, "baixar_arquivo"):
        client.baixar_arquivo(url, destino)
    else:
        destino.write_bytes(client.get_bytes(url))
