"""Quem trabalha no gabinete de cada parlamentar.

Câmara: arquivo dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv.
  Secretários parlamentares trazem em `uriLotacao` o id do deputado. O cargo
  vem como nível (ex.: SP20C); o salário de cada nível é fixado em lei.
  As páginas de remuneração individual da Câmara são bloqueadas para robôs
  (robots.txt), por isso não são coletadas.
Senado: API administrativa /api/v1/servidores/servidores, lotação
  "Gabinete do Senador Fulano". O nome é casado com o nome parlamentar.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select

from ..db import Assessor, Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import ler_csv

logger = logging.getLogger(__name__)

CAMARA_URL = "https://dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv"
SENADO_URL = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/servidores/servidores"
_ID_DEPUTADO = re.compile(r"/deputados/(\d+)")
_GABINETE_SENADO = re.compile(r"^gabinete d[ao] senador[a]?\s+(.+)$", re.I)


def _chave_nome(nome: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.lower().split())


def _casar(nome: str, senadores: Dict[str, int]) -> Optional[int]:
    """Casa o nome do gabinete com o nome parlamentar. Primeiro exato; depois,
    se um nome contém todas as palavras do outro e só há um candidato
    (ex.: gabinete "Weverton Rocha" e nome parlamentar "Weverton")."""
    if nome in senadores:
        return senadores[nome]
    palavras = set(nome.split())
    candidatos = [
        cod for chave, cod in senadores.items()
        if set(chave.split()) <= palavras or palavras <= set(chave.split())
    ]
    return candidatos[0] if len(candidatos) == 1 else None


def _substituir(casa: str, linhas: List[Dict[str, Any]]) -> int:
    with sessao() as s:
        s.execute(delete(Assessor).where(Assessor.casa == casa))
        if linhas:
            s.execute(insert(Assessor), linhas)
    return len(linhas)


def coletar_camara(client: HttpClient) -> int:
    linhas = []
    for r in ler_csv(client.get_bytes(CAMARA_URL)):
        m = _ID_DEPUTADO.search(r.get("uriLotacao") or "")
        if not m:
            continue
        linhas.append(
            {
                "casa": "camara",
                "codigo_politico": int(m.group(1)),
                "nome": n.texto(r.get("nome")) or "",
                "cargo": n.texto(r.get("grupo")),
                "funcao": n.texto(r.get("cargo")),  # nível, ex.: SP20C
                "lotacao": n.texto(r.get("lotacao")),
                "desde": n.data(r.get("dataInicioHistorico")) or n.data(r.get("dataNomeacao")),
            }
        )
    total = _substituir("camara", linhas)
    logger.info("Câmara: %s pessoas em gabinetes", total)
    return total


def coletar_senado(client: HttpClient) -> int:
    with sessao() as s:
        senadores = {
            _chave_nome(nome): cod
            for nome, cod in s.execute(
                select(Politico.nome, Politico.codigo).where(Politico.casa == "senado")
            ).all()
        }
    linhas, sem_par = [], set()
    for r in client.get_json(SENADO_URL):
        if (r.get("situacao") or "").upper() != "ATIVO":
            continue
        lotacao = n.texto((r.get("lotacao") or {}).get("nome")) or ""
        m = _GABINETE_SENADO.match(lotacao)
        if not m:
            continue
        codigo: Optional[int] = _casar(_chave_nome(m.group(1)), senadores)
        if codigo is None:
            sem_par.add(lotacao)
        linhas.append(
            {
                "casa": "senado",
                "codigo_politico": codigo,
                "nome": n.texto(r.get("nome")) or "",
                "cargo": n.texto((r.get("cargo") or {}).get("nome")) or n.texto(r.get("vinculo")),
                "funcao": n.texto(r.get("funcao")),
                "lotacao": lotacao,
                "desde": None,
            }
        )
    if sem_par:
        logger.warning("Senado: %s gabinetes sem senador correspondente: %s", len(sem_par), sorted(sem_par)[:10])
    total = _substituir("senado", linhas)
    logger.info("Senado: %s pessoas em gabinetes", total)
    return total
