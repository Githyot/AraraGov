"""Prefeitos, vices e vereadores eleitos, pelo TSE (fase 1 de docs/municipios.md).

Lê os arquivos de candidaturas das eleições municipais (2016, 2020, 2024) e
grava, para cada município, um `resumo.md` no formato araragov-md/1 com quem
foi eleito em cada mandato, e um `indice.md` com todos os municípios.

O TSE identifica municípios por um código próprio (SG_UE). O resto do
projeto usa o código do IBGE (Siconfi, TCEs), então os dois são ligados pelo
nome dentro do estado, com a lista de municípios do IBGE. Os poucos nomes que
mudaram ou são escritos de outro jeito ficam em
`araragov/referencia/municipios_tse_ibge.csv`.

CPF, título de eleitor, data de nascimento e e-mail existem no arquivo do
TSE, mas não são lidos nem gravados.
"""

from __future__ import annotations

import csv
import io
import logging
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .. import normalizar as n
from ..collectors.tse import CANDIDATOS_URL, UFS, _titulo
from . import md

logger = logging.getLogger(__name__)

IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
ANOS = (2016, 2020, 2024)

ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA", "ELEITO POR MEDIA"}
CARGOS = {"PREFEITO": "Prefeito", "VICE-PREFEITO": "Vice-prefeito", "VEREADOR": "Vereador"}
ORDEM_CARGO = {"Prefeito": 0, "Vice-prefeito": 1, "Vereador": 2}
_VAZIO = {"", "#NULO", "#NULO#", "#NE", "#NE#"}

COLUNAS_MANDATOS = [
    "eleicao", "inicio", "fim", "cargo", "nome", "nome_civil", "numero", "partido",
    "genero", "situacao", "sq_candidato", "cd_eleicao",
]
COLUNAS_SEM_DADOS = ["secao", "esfera", "responsavel", "motivo", "obrigacao", "fonte_consultada", "consultado_em"]
COLUNAS_INDICE = ["ibge", "tse", "municipio", "uf", "prefeito", "partido", "mandato", "vereadores"]


def mandato(ano_eleicao: int) -> Tuple[int, int]:
    """Eleição de 2024 -> mandato de 2025 a 2028."""
    return ano_eleicao + 1, ano_eleicao + 4


def chave_nome(nome: str) -> str:
    """Normaliza nomes de município para comparar TSE e IBGE:
    "Olhos-d'Água" e "OLHOS D AGUA" viram "OLHOS D AGUA"."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn"
    )
    limpo = "".join(c if c.isalnum() else " " for c in sem_acento.upper())
    return " ".join(limpo.split())


def _valor(linha: Dict[str, str], campo: str) -> Optional[str]:
    v = (linha.get(campo) or "").strip()
    return None if v.upper() in _VAZIO else v


# --- municípios do IBGE --------------------------------------------------------


def _uf_ibge(m: Dict[str, Any]) -> Optional[str]:
    # Municípios novos às vezes vêm sem microrregião; a região imediata é mais
    # confiável.
    for caminho in (("regiao-imediata", "regiao-intermediaria", "UF"), ("microrregiao", "mesorregiao", "UF")):
        atual: Any = m
        for parte in caminho:
            atual = atual.get(parte) if isinstance(atual, dict) else None
        if isinstance(atual, dict) and atual.get("sigla"):
            return atual["sigla"]
    return None


def municipios_ibge(client) -> Dict[Tuple[str, str], Tuple[int, str]]:
    """(UF, nome normalizado) -> (código IBGE, nome oficial)."""
    saida: Dict[Tuple[str, str], Tuple[int, str]] = {}
    for m in client.get_json(IBGE_MUNICIPIOS_URL):
        uf = _uf_ibge(m)
        if uf:
            saida[(uf, chave_nome(m["nome"]))] = (int(m["id"]), m["nome"])
    return saida


def correcoes_tse_ibge() -> Dict[Tuple[str, int], int]:
    """(UF, código TSE) -> código IBGE, para nomes que não batem."""
    texto = resources.files("araragov").joinpath("referencia/municipios_tse_ibge.csv").read_text(encoding="utf-8")
    linhas = (l for l in texto.splitlines() if l.strip() and not l.startswith("#"))
    return {
        (r["uf"].strip().upper(), int(r["tse"])): int(r["ibge"])
        for r in csv.DictReader(linhas, delimiter=";")
        if r.get("ibge", "").strip()
    }


# --- candidaturas ----------------------------------------------------------------


def _linhas(conteudo: bytes, ufs: Iterable[str]) -> Iterator[Dict[str, str]]:
    ufs = set(ufs)
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in sorted(z.namelist()):
            uf = nome.rsplit("_", 1)[-1].removesuffix(".csv")
            if not nome.endswith(".csv") or uf not in ufs:
                continue
            with z.open(nome) as f:
                yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";")


@dataclass
class Eleito:
    uf: str
    tse: int
    municipio: str
    dados: Dict[str, Any]


def eleitos_do_ano(conteudo: bytes, ano: int, ufs: Iterable[str] = UFS) -> List[Eleito]:
    """Eleitos de uma eleição municipal ordinária, já sem dados pessoais."""
    titulares: Dict[Tuple[int, str, int], Eleito] = {}
    vices: Dict[Tuple[int, int], Eleito] = {}
    for linha in _linhas(conteudo, ufs):
        tipo = (_valor(linha, "NM_TIPO_ELEICAO") or "").upper()
        if tipo and "ORDIN" not in tipo:
            continue  # eleições suplementares ficam para depois
        cargo = CARGOS.get((_valor(linha, "DS_CARGO") or "").upper())
        tse = n.inteiro(_valor(linha, "SG_UE"))
        numero = n.inteiro(_valor(linha, "NR_CANDIDATO"))
        uf = (_valor(linha, "SG_UF") or "").upper()
        if cargo is None or tse is None or numero is None or uf not in UFS:
            continue
        situacao = (_valor(linha, "DS_SIT_TOT_TURNO") or "").upper()
        social = _valor(linha, "NM_SOCIAL_CANDIDATO")
        inicio, fim = mandato(ano)
        e = Eleito(
            uf=uf,
            tse=tse,
            municipio=_titulo(_valor(linha, "NM_UE") or ""),
            dados={
                "eleicao": ano,
                "inicio": inicio,
                "fim": fim,
                "cargo": cargo,
                "nome": _titulo(_valor(linha, "NM_URNA_CANDIDATO") or ""),
                "nome_civil": _titulo(social or _valor(linha, "NM_CANDIDATO") or ""),
                "numero": numero,
                "partido": _valor(linha, "SG_PARTIDO"),
                "genero": _titulo(_valor(linha, "DS_GENERO") or "") or None,
                "situacao": _titulo(situacao) if situacao else None,
                "sq_candidato": _valor(linha, "SQ_CANDIDATO"),
                "cd_eleicao": _valor(linha, "CD_ELEICAO"),
            },
        )
        if cargo == "Vice-prefeito":
            # A linha do vice nem sempre traz "eleito"; ele entra se a chapa
            # (mesmo número no mesmo município) elegeu o prefeito.
            vices[(tse, numero)] = e  # a última linha (2º turno) prevalece
        elif situacao in ELEITO:
            titulares[(tse, cargo, numero)] = e
    eleitos = list(titulares.values())
    for (tse, cargo, numero), e in titulares.items():
        vice = vices.get((tse, numero)) if cargo == "Prefeito" else None
        if vice:
            vice.dados["situacao"] = e.dados["situacao"]
            eleitos.append(vice)
    return eleitos


# --- arquivos .md ------------------------------------------------------------------


def _ordenar(registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        registros,
        key=lambda r: (-r["eleicao"], ORDEM_CARGO.get(r["cargo"], 9), chave_nome(r["nome"] or "")),
    )


def gerar(
    client,
    saida: Path,
    anos: Iterable[int] = ANOS,
    ufs: Iterable[str] = UFS,
    hoje: Optional[date] = None,
) -> int:
    """Baixa os eleitos e grava v1/municipios/. Devolve o número de municípios."""
    hoje = hoje or date.today()
    ufs = [u.upper() for u in ufs]
    anos = sorted(anos)
    ibge = municipios_ibge(client)
    correcoes = correcoes_tse_ibge()

    por_municipio: Dict[Tuple[str, int], Dict[str, Any]] = {}
    anos_com_dado: Dict[Tuple[str, int], set] = {}
    for ano in anos:
        conteudo = client.get_bytes(CANDIDATOS_URL.format(ano=ano))
        eleitos = eleitos_do_ano(conteudo, ano, ufs)
        logger.info("TSE %s: %s eleitos municipais", ano, len(eleitos))
        for e in eleitos:
            m = por_municipio.setdefault((e.uf, e.tse), {"nome": e.municipio, "mandatos": []})
            if ano == anos[-1] or not m["nome"]:
                m["nome"] = e.municipio
            m["mandatos"].append(e.dados)
            anos_com_dado.setdefault((e.uf, e.tse), set()).add(ano)

    base = saida / "v1" / "municipios"
    indice: List[Dict[str, Any]] = []
    sem_ibge: List[str] = []
    for (uf, tse), m in sorted(por_municipio.items()):
        cod = correcoes.get((uf, tse))
        nome_oficial = m["nome"]
        if cod is None:
            achado = ibge.get((uf, chave_nome(m["nome"])))
            if achado:
                cod, nome_oficial = achado
        if cod is None:
            sem_ibge.append(f"{uf} {tse} {m['nome']}")
            continue
        sem_dados = [
            {
                "secao": "mandatos",
                "esfera": "federal",
                "responsavel": "Tribunal Superior Eleitoral (TSE)",
                "motivo": f"O arquivo de candidaturas de {ano} não tem eleitos deste município",
                "obrigacao": None,
                "fonte_consultada": CANDIDATOS_URL.format(ano=ano),
                "consultado_em": hoje,
            }
            for ano in anos
            if ano not in anos_com_dado[(uf, tse)]
        ]
        tabelas: Dict[str, List[Dict[str, Any]]] = {"mandatos": _ordenar(m["mandatos"])}
        if sem_dados:
            tabelas["sem-dados"] = sem_dados
        texto = md.escrever(
            {
                "tipo": "municipio-resumo",
                "ibge": cod,
                "tse": tse,
                "municipio": nome_oficial,
                "uf": uf,
                "atualizado": hoje,
                "fonte": "https://dadosabertos.tse.jus.br",
            },
            tabelas,
            colunas={"mandatos": COLUNAS_MANDATOS, "sem-dados": COLUNAS_SEM_DADOS},
            titulo=f"{nome_oficial} ({uf})",
            textos={
                "mandatos": "## Quem governa e governou\n\n"
                "Eleitos segundo o TSE. Quem assumiu depois (suplentes, eleições "
                "suplementares, cassações) ainda não aparece.",
                "sem-dados": "## Sem dados",
            },
        )
        caminho = base / uf.lower() / str(cod) / "resumo.md"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8")

        ultimo = max(anos_com_dado[(uf, tse)])
        atuais = [r for r in m["mandatos"] if r["eleicao"] == ultimo]
        prefeito = next((r for r in atuais if r["cargo"] == "Prefeito"), None)
        inicio, fim = mandato(ultimo)
        indice.append({
            "ibge": cod,
            "tse": tse,
            "municipio": nome_oficial,
            "uf": uf,
            "prefeito": prefeito["nome"] if prefeito else None,
            "partido": prefeito["partido"] if prefeito else None,
            "mandato": f"{inicio}-{fim}",
            "vereadores": sum(1 for r in atuais if r["cargo"] == "Vereador"),
        })

    if sem_ibge:
        logger.warning(
            "%s municípios do TSE sem código IBGE (adicione em referencia/municipios_tse_ibge.csv): %s",
            len(sem_ibge), "; ".join(sem_ibge),
        )
    base.mkdir(parents=True, exist_ok=True)
    (base / "indice.md").write_text(
        md.escrever(
            {"tipo": "municipios-indice", "atualizado": hoje, "anos": ",".join(map(str, anos)), "ufs": ",".join(ufs)},
            {"municipios": sorted(indice, key=lambda r: (r["uf"], chave_nome(r["municipio"])))},
            colunas={"municipios": COLUNAS_INDICE},
            titulo="Municípios no AraraGov",
        ),
        encoding="utf-8",
    )
    logger.info("Municípios: %s arquivos gravados, %s sem código IBGE", len(indice), len(sem_ibge))
    return len(indice)
