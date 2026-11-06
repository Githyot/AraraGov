"""Eleitos nos estados, a partir dos dados abertos do TSE.

O TSE publica, para cada eleição, um arquivo com todas as candidaturas e o
resultado. É a única fonte uniforme para os 27 estados: dá governadores,
vice-governadores e deputados estaduais/distritais com partido, gênero e
nome de urna.

Limites conhecidos (aparecem no app):
- O partido é o da eleição; trocas de partido depois não aparecem.
- Suplentes que assumiram depois não estão aqui. Onde a assembleia publica
  a lista de quem está em exercício (MG, SP), ela substitui esta.

Dados pessoais como CPF, título de eleitor e data de nascimento existem no
arquivo, mas não são lidos nem gravados.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from typing import Any, Dict, Iterator, Optional

from sqlalchemy import delete

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import gravar_politico

logger = logging.getLogger(__name__)

CANDIDATOS_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ano}.zip"

ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA", "ELEITO POR MEDIA"}

# DS_CARGO do TSE -> (prefixo da casa, cargo como aparece no app)
CARGOS = {
    "GOVERNADOR": ("gov", "Governador"),
    "VICE-GOVERNADOR": ("gov", "Vice-governador"),
    "DEPUTADO ESTADUAL": ("al", "Deputado estadual"),
    "DEPUTADO DISTRITAL": ("al", "Deputado distrital"),
}

# Código de cada eleição ordinária no DivulgaCandContas do TSE. Não é o
# CD_ELEICAO dos arquivos de dados abertos (2024 = 619 lá, 2045202024 aqui).
ELEICAO_DIVULGACAND = {
    2016: "2",
    2018: "2022802018",
    2020: "2030402020",
    2022: "2040602022",
    2024: "2045202024",
}
DIVULGACAND = "https://divulgacandcontas.tse.jus.br/divulga"


def url_foto(ano: int, sq_candidato: Optional[str], ue: Optional[str]) -> Optional[str]:
    """Foto pública da candidatura no DivulgaCandContas.

    `ue` é a unidade eleitoral: a sigla da UF nas eleições gerais, o código
    do município no TSE (SG_UE) nas municipais.
    """
    eleicao = ELEICAO_DIVULGACAND.get(ano)
    sq = (sq_candidato or "").strip()
    ue = (ue or "").strip()
    if not eleicao or not sq.isdigit() or not ue:
        return None
    return f"{DIVULGACAND}/rest/arquivo/img/{eleicao}/{sq}/{ue}"


UFS = (
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
).split()


def casa_estadual(prefixo: str, uf: str) -> str:
    """"al-mg" = Assembleia Legislativa de MG; "gov-mg" = governo de MG."""
    return f"{prefixo}-{uf.lower()}"


def _linhas(conteudo: bytes, ufs) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in sorted(z.namelist()):
            uf = nome.rsplit("_", 1)[-1].removesuffix(".csv")
            if not nome.endswith(".csv") or uf not in ufs:
                continue  # pula BRASIL/BR (nacionais) e o leiame
            texto = z.read(nome).decode("latin-1")
            yield from csv.DictReader(io.StringIO(texto), delimiter=";")


def _converter(linha: Dict[str, str], ano: int) -> Optional[Dict[str, Any]]:
    cargo = CARGOS.get(linha.get("DS_CARGO", "").strip().upper())
    if cargo is None or linha.get("DS_SIT_TOT_TURNO", "").strip().upper() not in ELEITO:
        return None
    numero = n.inteiro(linha.get("NR_CANDIDATO"))
    uf = (linha.get("SG_UF") or "").strip().upper()
    if numero is None or uf not in UFS:
        return None
    prefixo, nome_cargo = cargo
    if prefixo == "gov":
        # Governador e vice têm o mesmo número; o vice ganha um sufixo.
        numero = numero * 10 + (1 if nome_cargo == "Vice-governador" else 0)
    social = n.texto(linha.get("NM_SOCIAL_CANDIDATO"))
    return {
        "casa": casa_estadual(prefixo, uf),
        "cargo": nome_cargo,
        "codigo": numero,
        "nome": _titulo(n.texto(linha.get("NM_URNA_CANDIDATO")) or ""),
        "nome_civil": _titulo(social if social and social != "#NULO" else n.texto(linha.get("NM_CANDIDATO")) or ""),
        "partido": n.texto(linha.get("SG_PARTIDO")),
        "uf": uf,
        "sexo": _titulo(n.texto(linha.get("DS_GENERO")) or "") or None,
        "url_foto": url_foto(ano, linha.get("SQ_CANDIDATO"), uf),
        "email": None,
        # O TSE diz quem foi eleito, não quem está no cargo hoje; é a melhor
        # informação uniforme. O app avisa disso (ver exportar.AVISO_TSE).
        "em_exercicio": True,
        "legislatura": ano + 1,
        "fonte": "tse",
    }


_MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def _titulo(texto: str) -> str:
    """O TSE grava nomes em maiúsculas: "JOÃO DA SILVA" -> "João da Silva"."""
    palavras = texto.lower().split()
    return " ".join(
        p if (i and p in _MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palavras)
    )


def coletar_eleitos(
    client: HttpClient, ano: int = 2022, ufs=UFS, pular_casas: tuple = ()
) -> int:
    """Grava os eleitos estaduais de `ano`. `pular_casas` evita sobrescrever
    casas que têm lista própria e mais atual (ex.: "al-mg")."""
    conteudo = client.get_bytes(CANDIDATOS_URL.format(ano=ano))
    eleitos: Dict[tuple, Dict[str, Any]] = {}
    for linha in _linhas(conteudo, set(ufs)):
        dados = _converter(linha, ano)
        if dados and dados["casa"] not in pular_casas:
            # 2º turno repete o candidato; fica a última linha (resultado final)
            eleitos[(dados["casa"], dados["codigo"])] = dados

    casas = {c for c, _ in eleitos}
    with sessao() as s:
        # Recria as casas estaduais vindas do TSE, para não sobrar quem saiu.
        for casa in casas:
            atuais = {c for (c2, c) in eleitos if c2 == casa}
            s.execute(delete(Politico).where(Politico.casa == casa, Politico.codigo.not_in(atuais)))
        for dados in eleitos.values():
            gravar_politico(s, dados)
    por_cargo: Dict[str, int] = {}
    for d in eleitos.values():
        por_cargo[d["cargo"]] = por_cargo.get(d["cargo"], 0) + 1
    logger.info("TSE %s: %s eleitos estaduais em %s UFs %s", ano, len(eleitos), len({d["uf"] for d in eleitos.values()}), por_cargo)
    return len(eleitos)
