"""Benefícios além do salário.

Senado: a transparência publica um CSV com quem recebe auxílio-moradia e quem
ocupa imóvel funcional (um retrato do mês). O arquivo não traz o valor pago a
cada senador, então só o tipo de benefício é gravado.

Câmara: imóvel funcional, auxílio-moradia (com o valor do ano), viagens em
missão e passaporte diplomático vêm da página de cada deputado; ver
camara_recursos.py.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Dict, List

from sqlalchemy import delete, insert, select

from ..db import Beneficio, Politico, sessao
from ..http import HttpClient
from .gabinete import _casar, _chave_nome

logger = logging.getLogger(__name__)

SENADO_MORADIA_URL = "https://www.senado.leg.br/transparencia/lai/secrh/senador_auxilio_imoveis.csv"


def _sim(valor: str) -> bool:
    return (valor or "").strip().upper().startswith("SIM")


def coletar_moradia_senado(client: HttpClient) -> int:
    texto = client.get_bytes(SENADO_MORADIA_URL).decode("latin-1")
    linhas = texto.splitlines()
    # A 1ª linha é "ÚLTIMA ATUALIZAÇÃO;dd/mm/aaaa hh:mm"; o cabeçalho vem depois.
    referencia = None
    inicio = 0
    for i, linha in enumerate(linhas):
        if linha.upper().startswith("NOME;"):
            inicio = i
            break
        if ";" in linha:
            referencia = linha.split(";", 1)[1].strip()[:10] or None
    leitor = csv.reader(io.StringIO("\n".join(linhas[inicio + 1 :])), delimiter=";")

    with sessao() as s:
        senadores: Dict[str, int] = {
            _chave_nome(nome): cod
            for nome, cod in s.execute(select(Politico.nome, Politico.codigo).where(Politico.casa == "senado")).all()
        }
    registros: List[dict] = []
    sem_par = []
    for campos in leitor:
        if len(campos) < 5 or not campos[0].strip():
            continue
        nome, _uf, _partido, auxilio, imovel = (c.strip() for c in campos[:5])
        cod = _casar(_chave_nome(nome), senadores)
        if cod is None:
            sem_par.append(nome)
            continue
        base = {"casa": "senado", "codigo_politico": cod, "valor_mensal": None,
                "referencia": referencia, "fonte": SENADO_MORADIA_URL}
        if _sim(imovel):
            registros.append({**base, "tipo": "imovel_funcional", "descricao": "Ocupa imóvel funcional em Brasília"})
        if _sim(auxilio):
            registros.append({**base, "tipo": "auxilio_moradia", "descricao": "Recebe auxílio-moradia"})
    if sem_par:
        logger.warning("Senado: %s nomes sem senador correspondente na lista de moradia: %s", len(sem_par), sem_par[:5])
    with sessao() as s:
        s.execute(delete(Beneficio).where(Beneficio.casa == "senado", Beneficio.tipo.in_(("imovel_funcional", "auxilio_moradia"))))
        if registros:
            s.execute(insert(Beneficio), registros)
    logger.info("Senado: %s benefícios de moradia (%s)", len(registros), referencia)
    return len(registros)
