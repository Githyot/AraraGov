"""Assembleias legislativas com dados abertos próprios.

Onde a assembleia publica quem está em exercício e os gastos de cada
deputado, usamos a fonte dela em vez da lista de eleitos do TSE: ela inclui
suplentes que assumiram e o partido atual.

- ALMG (Minas Gerais): https://dadosabertos.almg.gov.br/ws/ajuda/sobre
  Deputados em exercício e verbas indenizatórias por deputado e mês, em JSON.
- Alesp (São Paulo): https://www.al.sp.gov.br/dados-abertos/
  Deputados e despesas de gabinete em XML. O arquivo de despesas traz todos
  os anos desde 2002 (mais de 100 MB), então é baixado uma vez por execução.
"""

from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import delete, select

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import gravar_politico, substituir_despesas

logger = logging.getLogger(__name__)

# --- Minas Gerais -----------------------------------------------------------

ALMG = "al-mg"
ALMG_API = "https://dadosabertos.almg.gov.br/ws"
ALMG_PERFIL = "https://www.almg.gov.br/deputados/conheca_deputados/deputados-info.html?idDep={id}"


def _almg(client: HttpClient, caminho: str) -> Any:
    return client.get_json(f"{ALMG_API}/{caminho}", {"formato": "json"})


def _data_almg(valor: Any) -> Optional[date]:
    if isinstance(valor, dict):  # {"@class": "sql-timestamp", "$": "2025-03-11"}
        valor = valor.get("$")
    return n.data(valor)


def coletar_deputados_almg(client: HttpClient) -> int:
    lista = _almg(client, "deputados/em_exercicio").get("list") or []
    ids = []
    with sessao() as s:
        for item in lista:
            cod = n.inteiro(item.get("id"))
            if cod is None:
                continue
            ids.append(cod)
            detalhe = (_almg(client, f"deputados/{cod}") or {}).get("deputado") or {}
            sexo = {"M": "Masculino", "F": "Feminino"}.get(detalhe.get("sexo"))
            gravar_politico(
                s,
                {
                    "casa": ALMG,
                    "cargo": "Deputado estadual",
                    "codigo": cod,
                    "nome": n.texto(item.get("nome")),
                    "nome_civil": None,
                    "partido": n.texto(item.get("partido")),
                    "uf": "MG",
                    "sexo": sexo,
                    "url_foto": None,
                    "email": None,
                    "em_exercicio": True,
                    "legislatura": 20,
                },
            )
        # Quem saiu do exercício (ou veio da lista do TSE) deixa a lista.
        s.execute(delete(Politico).where(Politico.casa == ALMG, Politico.codigo.not_in(ids)))
    logger.info("ALMG: %s deputados em exercício", len(ids))
    return len(ids)


def _linhas_almg(itens: List[Dict[str, Any]], cod: int, nome: str, ano: int, mes: int) -> Iterator[Dict[str, Any]]:
    for grupo in itens:
        for d in grupo.get("listaDetalheVerba") or [grupo]:
            valor = n.decimal(d.get("valorReembolsado", d.get("valor")))
            if valor is None:
                continue
            yield {
                "casa": ALMG,
                "chave_fonte": f"{cod}:{ano}-{mes:02d}:{d.get('codTipoDespesa')}:{d.get('id')}:{d.get('descDocumento')}",
                "codigo_politico": cod,
                "nome_politico": nome,
                "ano": ano,
                "mes": mes,
                "categoria": n.texto(d.get("descTipoDespesa") or grupo.get("descTipoDespesa")),
                "fornecedor": n.texto(d.get("nomeEmitente")),
                "cnpj_cpf": n.texto(d.get("cpfCnpj")),
                "data_documento": _data_almg(d.get("dataEmissao")),
                "valor": valor,
                "url_documento": ALMG_PERFIL.format(id=cod),
            }


def coletar_despesas_almg(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    with sessao() as s:
        deputados = s.execute(select(Politico.codigo, Politico.nome).where(Politico.casa == ALMG)).all()
    if not deputados:
        raise RuntimeError("Nenhum deputado da ALMG no banco. Rode antes: araragov coletar almg-deputados")
    hoje = date.today()
    ultimo_mes = 12 if ano < hoje.year else hoje.month
    linhas: List[Dict[str, Any]] = []
    for i, (cod, nome) in enumerate(deputados):
        if limite and i >= limite:
            break
        for mes in range(1, ultimo_mes + 1):
            itens = _almg(client, f"prestacao_contas/verbas_indenizatorias/deputados/{cod}/{ano}/{mes}").get("list") or []
            linhas.extend(_linhas_almg(itens, cod, nome, ano, mes))
    with sessao() as s:
        total = substituir_despesas(s, ALMG, ano, linhas)
    logger.info("ALMG: %s verbas indenizatórias gravadas em %s", total, ano)
    return total


# --- São Paulo --------------------------------------------------------------

ALESP = "al-sp"
ALESP_DADOS = "https://www.al.sp.gov.br/repositorioDados/deputados"
ALESP_DEPUTADOS = f"{ALESP_DADOS}/deputados.xml"
ALESP_DESPESAS = f"{ALESP_DADOS}/despesas_gabinetes.xml"
ALESP_PERFIL = "https://www.al.sp.gov.br/deputado/?matricula={matricula}"

_cache_despesas: Dict[int, bytes] = {}


def coletar_deputados_alesp(client: HttpClient) -> int:
    raiz = ET.fromstring(client.get_bytes(ALESP_DEPUTADOS))
    ids = []
    with sessao() as s:
        for d in raiz.iter("Deputado"):
            cod = n.inteiro(d.findtext("IdDeputado"))
            if cod is None:
                continue
            ids.append(cod)
            gravar_politico(
                s,
                {
                    "casa": ALESP,
                    "cargo": "Deputado estadual",
                    "codigo": cod,
                    "nome": n.texto(d.findtext("NomeParlamentar")),
                    "nome_civil": None,
                    "partido": n.texto(d.findtext("Partido")),
                    "uf": "SP",
                    "sexo": None,
                    "url_foto": None,
                    "email": n.texto(d.findtext("Email")),
                    "em_exercicio": (d.findtext("Situacao") or "").strip() == "EXE",
                    "legislatura": 20,
                },
            )
        s.execute(delete(Politico).where(Politico.casa == ALESP, Politico.codigo.not_in(ids)))
    logger.info("Alesp: %s deputados", len(ids))
    return len(ids)


def _matriculas_alesp(client: HttpClient) -> Dict[str, int]:
    raiz = ET.fromstring(client.get_bytes(ALESP_DEPUTADOS))
    return {
        (d.findtext("Matricula") or "").strip(): int(d.findtext("IdDeputado"))
        for d in raiz.iter("Deputado")
        if (d.findtext("IdDeputado") or "").strip().isdigit()
    }


def _linhas_alesp(conteudo: bytes, ano: int, matriculas: Dict[str, int], limite: Optional[int]) -> Iterator[Dict[str, Any]]:
    repetidas: Counter = Counter()
    total = 0
    for _, el in ET.iterparse(io.BytesIO(conteudo)):
        if el.tag != "despesa":
            continue
        campos = {c.tag: (c.text or "").strip() for c in el}
        el.clear()
        if n.inteiro(campos.get("Ano")) != ano:
            continue
        valor = n.decimal(campos.get("Valor"))
        mes = n.inteiro(campos.get("Mes")) or 0
        if valor is None:
            continue
        matricula = campos.get("Matricula", "")
        # A fonte não tem id por despesa; a chave junta os campos e um contador
        # para despesas idênticas no mesmo mês.
        base = f"{matricula}:{ano}-{mes:02d}:{campos.get('Tipo', '')[:40]}:{campos.get('CNPJ', '')}:{valor}"
        repetidas[base] += 1
        yield {
            "casa": ALESP,
            "chave_fonte": f"{base}:{repetidas[base]}"[:120],
            "codigo_politico": matriculas.get(matricula),
            "nome_politico": n.texto(campos.get("Deputado")),
            "ano": ano,
            "mes": mes,
            "categoria": n.texto(campos.get("Tipo")),
            "fornecedor": n.texto(campos.get("Fornecedor")),
            "cnpj_cpf": n.texto(campos.get("CNPJ")),
            "data_documento": None,
            "valor": valor,
            "url_documento": ALESP_PERFIL.format(matricula=matricula) if matricula else None,
        }
        total += 1
        if limite and total >= limite:
            return


def coletar_despesas_alesp(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    chave = id(client)
    if chave not in _cache_despesas:
        _cache_despesas.clear()
        _cache_despesas[chave] = client.get_bytes(ALESP_DESPESAS)
    matriculas = _matriculas_alesp(client)
    with sessao() as s:
        total = substituir_despesas(s, ALESP, ano, _linhas_alesp(_cache_despesas[chave], ano, matriculas, limite))
    logger.info("Alesp: %s despesas de gabinete gravadas em %s", total, ano)
    return total
