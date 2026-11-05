"""Fase 5: fornecedores de cada município, com fatos documentados sobre eles.

Junta, por município, as empresas (CNPJ) que aparecem nos pagamentos e nos
contratos das fases anteriores e acrescenta só o que está em fonte pública:

- Sanções no CEIS (empresas inidôneas e impedidas) e no CNEP (Lei
  Anticorrupção), do Portal da Transparência (CGU).
- Serviço prestado à campanha de um candidato do mesmo município, declarado
  pelo próprio candidato ao TSE (despesas contratadas), com a indicação de que
  o candidato foi eleito.

Nada disso é acusação. Uma gráfica pode imprimir santinhos e depois vender à
prefeitura de forma regular; o app mostra o fato com a fonte para que o
leitor possa perguntar. Sanções e campanhas de pessoas físicas (CPF) não são
lidas. Os sócios das empresas (base de CNPJ da Receita) ainda não entram: o
servidor da Receita não responde à coleta automática, e o arquivo diz isso na
tabela `sem-dados`.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import time
import zipfile
from functools import lru_cache
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from . import md
from .eleitos import COLUNAS_SEM_DADOS, chave_nome, correcoes_tse_ibge, municipios_ibge
from .tcesp import _resumir, formatar_cnpj, so_digitos, valor

logger = logging.getLogger(__name__)

SANCOES_URL = "https://portaldatransparencia.gov.br/download-de-dados/{cadastro}/{data}"
SANCOES_PAGINA = "https://portaldatransparencia.gov.br/sancoes/{cadastro}"
CAMPANHA_URL = ("https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/"
                "prestacao_de_contas_eleitorais_candidatos_{ano}.zip")
CAMPANHA_PAGINA = "https://divulgacandcontas.tse.jus.br/"
RECEITA_CNPJ = "https://dadosabertos.rfb.gov.br/CNPJ/"

TOP_FORNECEDORES = 100
# Empresa que serviu a campanhas em muitos municípios é plataforma ou
# serviço de massa (rede social, telefonia, combustível); o cruzamento com a
# prefeitura não diz nada e fica de fora.
MAX_MUNICIPIOS_CAMPANHA = 15

COLUNAS_FORNECEDORES = ["cnpj", "empresa", "pago", "anos_pagos", "contratos", "valor_contratos", "indicios"]
COLUNAS_SANCOES = ["cnpj", "empresa", "cadastro", "sancao", "inicio", "fim", "orgao", "uf_orgao", "esfera",
                   "abrangencia", "processo", "fundamento", "fonte"]
COLUNAS_CAMPANHA = ["cnpj", "empresa", "eleicao", "candidato", "cargo", "partido", "eleito", "valor", "servico", "fonte"]


# --- leitura das fontes -------------------------------------------------------------------


def _csv_do_zip(arquivo: Path, filtro) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(arquivo) as z:
        for nome in sorted(z.namelist()):
            if nome.lower().endswith(".csv") and filtro(nome):
                with z.open(nome) as f:
                    yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def _data_br(texto: Optional[str]) -> Optional[str]:
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (texto or "").strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def ler_sancoes(linhas: Iterable[Dict[str, str]], cnpjs: Optional[Set[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """CNPJ -> sanções (CEIS ou CNEP). Pessoas físicas são ignoradas."""
    por_cnpj: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for l in linhas:
        if (l.get("TIPO DE PESSOA") or "").strip().upper() != "J":
            continue
        cnpj = so_digitos(l.get("CPF OU CNPJ DO SANCIONADO"))
        if len(cnpj) != 14 or (cnpjs is not None and cnpj not in cnpjs):
            continue
        cadastro = (l.get("CADASTRO") or "").strip().upper()
        por_cnpj[cnpj].append({
            "cnpj": formatar_cnpj(cnpj),
            "empresa": _resumir(l.get("RAZÃO SOCIAL - CADASTRO RECEITA") or l.get("NOME DO SANCIONADO"), 120),
            "cadastro": cadastro,
            "sancao": _resumir(l.get("CATEGORIA DA SANÇÃO"), 120),
            "inicio": _data_br(l.get("DATA INÍCIO SANÇÃO")),
            "fim": _data_br(l.get("DATA FINAL SANÇÃO")),
            "orgao": _resumir(l.get("ÓRGÃO SANCIONADOR"), 120),
            "uf_orgao": (l.get("UF ÓRGÃO SANCIONADOR") or "").strip() or None,
            "esfera": (l.get("ESFERA ÓRGÃO SANCIONADOR") or "").strip().title() or None,
            "abrangencia": _resumir(l.get("ABRAGÊNCIA DA SANÇÃO") or l.get("ABRANGÊNCIA DA SANÇÃO"), 80),
            "processo": (l.get("NÚMERO DO PROCESSO") or "").strip() or None,
            "fundamento": _resumir(l.get("FUNDAMENTAÇÃO LEGAL"), 160),
            "fonte": SANCOES_PAGINA.format(cadastro=cadastro.lower() or "ceis"),
        })
    return por_cnpj


@dataclass
class Campanha:
    """Serviços de uma empresa à campanha de um candidato (soma das despesas)."""
    cnpj: str
    empresa: str
    eleicao: int
    sq_candidato: str
    candidato: str
    cargo: str
    partido: str
    valor: Decimal = Decimal(0)
    servicos: Set[str] = field(default_factory=set)


def ler_campanhas(linhas: Iterable[Dict[str, str]], ano: int, tse_ibge, cnpjs_por_mun: Dict[int, Set[str]],
                  alcance: Optional[Dict[str, Set[str]]] = None) -> Dict[int, Dict[Tuple[str, str], Campanha]]:
    """IBGE -> (cnpj, sq_candidato) -> Campanha, só para empresas que também
    receberam do mesmo município. Se `alcance` for dado, anota nele em
    quantos municípios cada CNPJ serviu a campanhas (todos, sem filtro)."""
    saida: Dict[int, Dict[Tuple[str, str], Campanha]] = defaultdict(dict)
    for l in linhas:
        if (l.get("CD_TIPO_ELEICAO") or "").strip() != "2":  # só eleição ordinária
            continue
        cnpj = so_digitos(l.get("NR_CPF_CNPJ_FORNECEDOR"))
        if len(cnpj) != 14:
            continue
        if alcance is not None:
            alcance.setdefault(cnpj, set()).add(f"{l.get('SG_UF')}-{l.get('SG_UE')}")
        ibge = tse_ibge(l.get("SG_UF"), l.get("SG_UE"), l.get("NM_UE"))
        if ibge is None or cnpj not in cnpjs_por_mun.get(ibge, ()):
            continue
        sq = (l.get("SQ_CANDIDATO") or "").strip()
        chave = (cnpj, sq)
        c = saida[ibge].get(chave)
        if c is None:
            c = saida[ibge][chave] = Campanha(
                cnpj=cnpj, empresa=_resumir(l.get("NM_FORNECEDOR_RFB") or l.get("NM_FORNECEDOR"), 120), eleicao=ano,
                sq_candidato=sq, candidato=(l.get("NM_CANDIDATO") or "").strip(),
                cargo=(l.get("DS_CARGO") or "").strip().capitalize(), partido=(l.get("SG_PARTIDO") or "").strip())
        c.valor += valor(l.get("VR_DESPESA_CONTRATADA"))
        servico = _resumir(l.get("DS_ORIGEM_DESPESA"), 80)
        if servico and servico != "#NULO":
            c.servicos.add(servico)
    return saida


def remover_plataformas(campanhas: Dict[int, Dict[Tuple[str, str], Campanha]],
                        alcance: Optional[Dict[str, Set[str]]] = None) -> Dict[int, Dict[Tuple[str, str], Campanha]]:
    municipios: Dict[str, Set] = defaultdict(set)
    for ibge, d in campanhas.items():
        for c in d.values():
            municipios[c.cnpj].add(ibge)
    for cnpj, ues in (alcance or {}).items():
        if cnpj in municipios and len(ues) > len(municipios[cnpj]):
            municipios[cnpj] = ues
    fora = {c for c, m in municipios.items() if len(m) > MAX_MUNICIPIOS_CAMPANHA}
    if fora:
        logger.info("Campanhas: %s empresas de serviço de massa fora do cruzamento", len(fora))
    return {ibge: {k: c for k, c in d.items() if c.cnpj not in fora} for ibge, d in campanhas.items()}


def tradutor_tse_ibge():
    """Função (UF, código TSE, nome) -> código IBGE, igual à da fase 1."""
    ibge = municipios_ibge()
    correcoes = correcoes_tse_ibge()

    @lru_cache(maxsize=None)
    def traduz(uf, tse, nome) -> Optional[int]:
        uf = (uf or "").strip().upper()
        try:
            cod = correcoes.get((uf, int(tse)))
        except (TypeError, ValueError):
            cod = None
        if cod:
            return cod
        achado = ibge.get((uf, chave_nome(nome or "")))
        return achado[0] if achado else None

    return traduz


# --- fornecedores das fases anteriores ----------------------------------------------------


@dataclass
class Fornecedor:
    empresa: str = ""
    pago: Decimal = Decimal(0)
    anos_pagos: Set[int] = field(default_factory=set)
    contratos: int = 0
    valor_contratos: Decimal = Decimal(0)


def _ler(caminho: Path) -> Optional[md.Documento]:
    try:
        return md.ler(caminho.read_text(encoding="utf-8"))
    except (OSError, md.ErroFormato):
        logger.warning("Não foi possível ler %s", caminho)
        return None


def fornecedores_do_municipio(pasta: Path) -> Dict[str, Fornecedor]:
    """CNPJ (só dígitos) -> totais, a partir de {ano}-pagamentos.md e {ano}-contratos.md."""
    por: Dict[str, Fornecedor] = defaultdict(Fornecedor)
    for arq in sorted(pasta.glob("*-pagamentos.md")):
        doc = _ler(arq)
        if not doc:
            continue
        ano = int(doc.meta.get("ano", arq.name[:4]))
        for r in doc.tabelas.get("favorecidos", []):
            c = so_digitos(r.get("cnpj"))
            if len(c) == 14:
                f = por[c]
                f.empresa = f.empresa or r.get("favorecido") or ""
                f.pago += md.numero(r.get("pago")) or Decimal(0)
                f.anos_pagos.add(ano)
    for arq in sorted(pasta.glob("*-contratos.md")):
        doc = _ler(arq)
        if not doc:
            continue
        vistos = set()
        for tabela in ("contratos", "obras"):
            for r in doc.tabelas.get(tabela, []):
                c = so_digitos(r.get("cnpj"))
                chave = (c, r.get("contrato"), r.get("orgao"))
                if len(c) != 14 or chave in vistos:
                    continue
                vistos.add(chave)
                f = por[c]
                f.empresa = f.empresa or r.get("empresa") or ""
                f.contratos += 1
                f.valor_contratos += md.numero(r.get("valor")) or Decimal(0)
        for r in doc.tabelas.get("contratacoes-diretas", []):
            c = so_digitos(r.get("cnpj"))
            if len(c) == 14:
                por[c].empresa = por[c].empresa or r.get("empresa") or ""
    return dict(por)


def eleitos_do_municipio(pasta: Path) -> Dict[str, str]:
    """sq_candidato -> "Prefeito 2025-2028", pelo resumo.md da fase 1."""
    caminho = pasta / "resumo.md"
    doc = _ler(caminho) if caminho.exists() else None
    if not doc:
        return {}
    return {r["sq_candidato"]: f"{r['cargo']} {r['inicio']}-{r['fim']}"
            for r in doc.tabelas.get("mandatos", []) if r.get("sq_candidato")}


def emendas_do_municipio(pasta: Path) -> Dict[str, List[str]]:
    """CNPJ (só dígitos) -> ["AUTOR 2025", ...], pelo emendas.md da fase 6
    (só favorecidos que não são a prefeitura)."""
    caminho = pasta / "emendas.md"
    doc = _ler(caminho) if caminho.exists() else None
    saida: Dict[str, List[str]] = defaultdict(list)
    for r in (doc.tabelas.get("recebido", []) if doc else []):
        c = so_digitos(r.get("cnpj"))
        rotulo = f"{r.get('autor') or 'autor não informado'} {r.get('ano')}"
        if len(c) == 14 and "MUNICIPIO" not in (r.get("natureza") or "").upper() and rotulo not in saida[c]:
            saida[c].append(rotulo)
    return dict(saida)


# --- documento -----------------------------------------------------------------------------


def documento(ibge: int, mun: str, uf: str, fornecedores: Dict[str, Fornecedor],
              sancoes: Dict[str, List[Dict[str, Any]]], campanhas: Dict[Tuple[str, str], Campanha],
              eleitos: Dict[str, str], eleicoes: Iterable[int], hoje: date, data_sancoes: Optional[str],
              emendas: Optional[Dict[str, List[str]]] = None) -> str:
    emendas = emendas or {}
    campanha_por_cnpj: Dict[str, List[Campanha]] = defaultdict(list)
    for c in campanhas.values():
        campanha_por_cnpj[c.cnpj].append(c)

    def indicios(cnpj: str) -> Optional[str]:
        partes = []
        for s in sorted(sancoes.get(cnpj, []), key=lambda s: s.get("inicio") or "", reverse=True)[:2]:
            periodo = "-".join(x[:4] for x in (s.get("inicio"), s.get("fim")) if x)
            partes.append(f"Sanção no {s['cadastro']} ({', '.join(x for x in (s.get('orgao'), periodo) if x)})")
        anos = sorted({c.eleicao for c in campanha_por_cnpj.get(cnpj, [])})
        if anos:
            partes.append("Fornecedora de campanha (" + ", ".join(map(str, anos)) + ")")
        if cnpj in emendas:
            partes.append("Recebeu emenda federal direto (" + ", ".join(emendas[cnpj][:3]) + ")")
        return "; ".join(partes) or None

    ordem = sorted(fornecedores.items(), key=lambda kv: (kv[1].pago + kv[1].valor_contratos), reverse=True)
    destaque = [c for c, _ in ordem if indicios(c)]
    escolhidos = list(dict.fromkeys(destaque + [c for c, _ in ordem[:TOP_FORNECEDORES]]))
    linhas = [{
        "cnpj": formatar_cnpj(c), "empresa": fornecedores[c].empresa, "pago": fornecedores[c].pago,
        "anos_pagos": ", ".join(map(str, sorted(fornecedores[c].anos_pagos))) or None,
        "contratos": fornecedores[c].contratos, "valor_contratos": fornecedores[c].valor_contratos,
        "indicios": indicios(c),
    } for c in escolhidos]
    linhas.sort(key=lambda r: (r["indicios"] is None, -(r["pago"] + r["valor_contratos"])))

    tab_sancoes = [s for c in escolhidos for s in sancoes.get(c, [])]
    tab_campanha = sorted(({
        "cnpj": formatar_cnpj(c.cnpj), "empresa": c.empresa, "eleicao": c.eleicao, "candidato": c.candidato,
        "cargo": c.cargo, "partido": c.partido,
        "eleito": f"Sim ({eleitos[c.sq_candidato]})" if c.sq_candidato in eleitos else "Não",
        "valor": c.valor, "servico": ", ".join(sorted(c.servicos)) or None, "fonte": CAMPANHA_PAGINA,
    } for c in campanhas.values()), key=lambda r: (r["eleito"] == "Não", -r["valor"]))

    sem = [{
        "secao": "socios", "esfera": "federal", "responsavel": "Receita Federal",
        "motivo": "A base pública de CNPJ (sócios e endereços) não respondeu à coleta automática; "
                  "vínculos por sócio ou endereço em comum ainda não foram verificados.",
        "obrigacao": "Dados abertos do CNPJ (Decreto 8.777/2016)", "fonte_consultada": RECEITA_CNPJ,
        "consultado_em": hoje.isoformat(),
    }]
    if not data_sancoes:
        sem.append({"secao": "sancoes", "esfera": "federal", "responsavel": "Controladoria-Geral da União",
                    "motivo": "O arquivo do CEIS/CNEP não foi baixado nesta coleta.", "obrigacao": "Lei 12.846/2013, art. 22 e 23",
                    "fonte_consultada": SANCOES_PAGINA.format(cadastro="ceis"), "consultado_em": hoje.isoformat()})
    meta = {"tipo": "municipio-fornecedores", "ibge": ibge, "municipio": mun, "uf": uf, "atualizado": hoje,
            "sancoes_em": data_sancoes, "eleicoes": ", ".join(map(str, sorted(eleicoes))) or None,
            "fonte": "TCE-SP, Portal da Transparência (CEIS/CNEP) e TSE (prestação de contas)"}
    return md.escrever(
        {k: v for k, v in meta.items() if v is not None},
        {"fornecedores": linhas, "sancoes": tab_sancoes, "campanha": tab_campanha, "sem-dados": sem},
        colunas={"fornecedores": COLUNAS_FORNECEDORES, "sancoes": COLUNAS_SANCOES,
                 "campanha": COLUNAS_CAMPANHA, "sem-dados": COLUNAS_SEM_DADOS},
        titulo=f"{mun} ({uf}), fornecedores",
        textos={
            "fornecedores": "## Empresas que receberam ou foram contratadas\n\nSoma dos pagamentos e dos "
            "contratos dos anos coletados. A coluna de indícios só aponta fatos com fonte pública; "
            "nenhum deles é prova de irregularidade.",
            "sancoes": "## Sanções registradas\n\nEmpresas desta lista que aparecem no CEIS ou no CNEP "
            "(CGU). Uma sanção pode ter sido aplicada por outro órgão, em outro estado, e pode valer "
            "só para aquele órgão: veja a abrangência e o período.",
            "campanha": "## Empresas que também serviram a campanhas no município\n\nServiços declarados "
            "pelos próprios candidatos ao TSE. Prestar serviço a uma campanha e depois vender à "
            "prefeitura não é proibido; o cruzamento serve para conferir. Empresas que serviram a "
            f"campanhas em mais de {MAX_MUNICIPIOS_CAMPANHA} municípios (redes sociais, telefonia) ficam de fora.",
            "sem-dados": "## O que ainda não há",
        },
    )


# --- coleta --------------------------------------------------------------------------------


def baixar_sancoes(client, pasta: Path, hoje: date) -> Tuple[Dict[str, List[Dict[str, Any]]], Optional[str]]:
    """Baixa CEIS e CNEP do dia mais recente disponível (até 7 dias atrás)."""
    for atraso in range(1, 8):
        dia = hoje - timedelta(days=atraso)
        arquivos = []
        try:
            for cadastro in ("ceis", "cnep"):
                arq = pasta / f"{cadastro}.zip"
                client.baixar_arquivo(SANCOES_URL.format(cadastro=cadastro, data=dia.strftime("%Y%m%d")), arq)
                if not zipfile.is_zipfile(arq):
                    raise RuntimeError(f"{cadastro} de {dia} não é um zip")
                arquivos.append(arq)
        except Exception as e:  # noqa: BLE001 - tenta o dia anterior
            logger.info("Sanções de %s indisponíveis: %s", dia, e)
            continue
        sancoes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for arq in arquivos:
            for cnpj, lista in ler_sancoes(_csv_do_zip(arq, lambda n: True)).items():
                sancoes[cnpj].extend(lista)
            arq.unlink(missing_ok=True)
        logger.info("Sanções (CEIS/CNEP) de %s: %s empresas", dia, len(sancoes))
        return dict(sancoes), dia.isoformat()
    logger.warning("CEIS/CNEP não baixados")
    return {}, None


def gerar(client, saida: Path, ufs: Iterable[str] = ("SP",), eleicoes: Iterable[int] = (2016, 2020, 2024),
          hoje: Optional[date] = None, pasta_tmp: Optional[Path] = None) -> int:
    hoje = hoje or date.today()
    pasta_tmp = pasta_tmp or saida.parent / "tmp"
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in ufs]
    pastas = {(uf, int(p.name)): p for uf in ufs
              for p in sorted((saida / "v1" / "municipios" / uf.lower()).glob("[0-9]*")) if p.is_dir()}
    fornecedores = {k: fornecedores_do_municipio(p) for k, p in pastas.items()}
    fornecedores = {k: v for k, v in fornecedores.items() if v}
    if not fornecedores:
        logger.warning("Nenhum fornecedor encontrado em %s (rode antes a coleta do TCE)", ufs)
        return 0
    todos = {c for f in fornecedores.values() for c in f}
    sancoes, data_sancoes = baixar_sancoes(client, pasta_tmp, hoje)
    sancoes = {c: s for c, s in sancoes.items() if c in todos}

    cnpjs_por_mun = {ibge: set(f) for (_, ibge), f in fornecedores.items()}
    traduz = tradutor_tse_ibge()
    campanhas: Dict[int, Dict[Tuple[str, str], Campanha]] = defaultdict(dict)
    lidas = []
    alcance: Dict[str, Set[str]] = {}
    for ano in sorted(eleicoes):
        arq = pasta_tmp / f"prestacao-{ano}.zip"
        try:
            inicio = time.monotonic()
            client.baixar_arquivo(CAMPANHA_URL.format(ano=ano), arq)
            logger.info("TSE %s: prestação de contas baixada em %.0f s", ano, time.monotonic() - inicio)
            padrao = re.compile(r"despesas_contratadas_candidatos_%d_(%s)\.csv$" % (ano, "|".join(ufs)), re.I)
            por = ler_campanhas(_csv_do_zip(arq, lambda n: bool(padrao.search(n))), ano, traduz, cnpjs_por_mun, alcance)
        except Exception as e:  # noqa: BLE001 - segue sem o ano
            logger.warning("Prestação de contas do TSE de %s não lida: %s", ano, e)
            continue
        finally:
            arq.unlink(missing_ok=True)
        lidas.append(ano)
        for ibge, d in por.items():
            campanhas[ibge].update(d)
        logger.info("TSE %s: %s municípios com fornecedor de campanha que também recebeu da prefeitura", ano, len(por))

    campanhas = remover_plataformas(campanhas, alcance)
    nomes = {cod: nome for (uf, _), (cod, nome) in municipios_ibge().items()}
    n = 0
    for (uf, ibge), forn in fornecedores.items():
        texto = documento(ibge, nomes.get(ibge, str(ibge)), uf, forn, sancoes, campanhas.get(ibge, {}),
                          eleitos_do_municipio(pastas[(uf, ibge)]), lidas, hoje, data_sancoes,
                          emendas_do_municipio(pastas[(uf, ibge)]))
        (pastas[(uf, ibge)] / "fornecedores.md").write_text(texto, encoding="utf-8")
        n += 1
    logger.info("Fornecedores: %s municípios, %s empresas com sanção, %s com serviço de campanha",
                n, len(sancoes), sum(len(c) for c in campanhas.values()))
    return n
