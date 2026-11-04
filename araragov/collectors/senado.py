"""Senado Federal.

Fontes (dados abertos, sem chave):
- Senadores em exercício: legis.senado.leg.br/dadosabertos/senador/lista/atual
- Votações nominais: /dadosabertos/votacao?codigoParlamentar=...  Este é o
  filtro que a fonte respeita (outros filtros são ignorados, conforme medido
  pelo projeto Mamute Político). Cada resposta traz os votos de todos os
  senadores, então cada votação é gravada uma única vez.
- Cota parlamentar (CEAPS): adm.senado.gov.br/adm-dadosabertos
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import select

from ..db import Politico, sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import gravar_politico, gravar_votacao, substituir_despesas

logger = logging.getLogger(__name__)

API = "https://legis.senado.leg.br/dadosabertos"
CEAPS_URL = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"
CEAPS_LINK = "https://www6g.senado.leg.br/transparencia/sen/{cod}/?ano={ano}"
CASA = "senado"


def _lista(valor: Any) -> List[Any]:
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def _get(d: Dict[str, Any], *chaves: str) -> Any:
    """A API do Senado alterna entre camelCase e PascalCase conforme a versão."""
    for c in chaves:
        if c in d and d[c] not in (None, ""):
            return d[c]
    return None


def coletar_senadores(client: HttpClient) -> int:
    dados = client.get_json(f"{API}/senador/lista/atual")
    parlamentares = _lista(
        ((dados.get("ListaParlamentarEmExercicio") or {}).get("Parlamentares") or {}).get("Parlamentar")
    )
    with sessao() as s:
        for p in parlamentares:
            ident = p.get("IdentificacaoParlamentar") or {}
            codigo = n.inteiro(ident.get("CodigoParlamentar"))
            if codigo is None:
                continue
            gravar_politico(
                s,
                {
                    "casa": CASA,
                    "cargo": "Senador",
                    "codigo": codigo,
                    "nome": n.texto(ident.get("NomeParlamentar")) or str(codigo),
                    "nome_civil": n.texto(ident.get("NomeCompletoParlamentar")),
                    "partido": n.texto(ident.get("SiglaPartidoParlamentar")),
                    "uf": n.texto(ident.get("UfParlamentar")),
                    "sexo": n.texto(ident.get("SexoParlamentar")),
                    "url_foto": n.texto(ident.get("UrlFotoParlamentar")),
                    "email": n.texto(ident.get("EmailParlamentar")),
                    "em_exercicio": True,
                },
            )
    logger.info("Senado: %s senadores gravados", len(parlamentares))
    return len(parlamentares)


def _votacoes(dados: Any) -> List[Dict[str, Any]]:
    """Extrai a lista de votações, tolerando os vários formatos da API."""
    if isinstance(dados, list):
        return [d for d in dados if isinstance(d, dict)]
    if isinstance(dados, dict):
        for chave in ("votacoes", "Votacoes", "ListaVotacoes", "Votacao", "votacao"):
            if chave in dados:
                return _votacoes(dados[chave])
        for valor in dados.values():
            achou = _votacoes(valor)
            if achou:
                return achou
    return []


def _converter(entrada: Dict[str, Any]) -> Optional[tuple]:
    codigo = _get(entrada, "codigoSessaoVotacao", "CodigoSessaoVotacao", "codigoVotacaoSve")
    if codigo is None:
        return None
    codigo = str(codigo)
    sigla, numero, ano = (
        _get(entrada, "sigla", "Sigla", "siglaMateria"),
        _get(entrada, "numero", "Numero", "numeroMateria"),
        _get(entrada, "ano", "Ano", "anoMateria"),
    )
    materia = _get(entrada, "codigoMateria", "CodigoMateria")
    votacao = {
        "id": f"{CASA}:{codigo}",
        "casa": CASA,
        "codigo": codigo,
        "data": n.data_hora(_get(entrada, "dataSessao", "DataSessao")),
        "orgao": "PLEN",
        "descricao": n.texto(_get(entrada, "descricaoVotacao", "DescricaoVotacao")),
        "proposicao": f"{sigla} {numero}/{ano}" if sigla else n.texto(_get(entrada, "identificacao")),
        "ementa": n.texto(_get(entrada, "ementa", "Ementa")),
        "resultado": n.texto(_get(entrada, "resultadoVotacao", "ResultadoVotacao")),
        "link": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{materia}" if materia else None,
        "orientacoes": None,
    }
    votos = []
    for v in _lista(_get(entrada, "votos", "Votos")):
        cod = n.inteiro(_get(v, "codigoParlamentar", "CodigoParlamentar"))
        if cod is None:
            continue
        original = n.texto(_get(v, "siglaVotoParlamentar", "SiglaVotoParlamentar", "descricaoVotoParlamentar"))
        votos.append(
            {
                "casa": CASA,
                "codigo_politico": cod,
                "nome_politico": n.texto(_get(v, "nomeParlamentar", "NomeParlamentar")),
                "partido": n.texto(_get(v, "siglaPartidoParlamentar", "SiglaPartidoParlamentar")),
                "uf": n.texto(_get(v, "siglaUFParlamentar", "siglaUfParlamentar", "SiglaUFParlamentar")),
                "voto_original": original,
                "voto": n.voto(original),
            }
        )
    return votacao, votos


def coletar_votacoes(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    with sessao() as s:
        codigos = s.execute(select(Politico.codigo).where(Politico.casa == CASA)).scalars().all()
    if not codigos:
        raise RuntimeError("Nenhum senador no banco. Rode antes: araragov coletar senado-senadores")

    # Filtrada por senador, a API devolve só o voto daquele senador em cada
    # sessão. Juntamos as respostas de todos para montar cada votação.
    votacoes: Dict[str, Dict[str, Any]] = {}
    votos_por: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for cod in codigos:
        dados = client.get_json(
            f"{API}/votacao",
            {"codigoParlamentar": cod, "dataInicio": f"{ano}-01-01", "dataFim": f"{ano}-12-31", "v": 1},
        )
        for entrada in _votacoes(dados):
            convertido = _converter(entrada)
            if convertido is None:
                continue
            votacao, votos = convertido
            vid = votacao["id"]
            if vid not in votacoes:
                if limite and len(votacoes) >= limite:
                    continue
                votacoes[vid] = votacao
                votos_por[vid] = {}
            for v in votos:
                votos_por[vid].setdefault(v["codigo_politico"], v)

    gravadas = 0
    with sessao() as s:
        for vid, votacao in votacoes.items():
            if votos_por[vid]:
                gravar_votacao(s, votacao, list(votos_por[vid].values()))
                gravadas += 1
    logger.info("Senado: %s votações nominais gravadas em %s", gravadas, ano)
    return gravadas


def _linhas_ceaps(itens: List[Dict[str, Any]], ano: int, limite: Optional[int]) -> Iterator[Dict[str, Any]]:
    for i, item in enumerate(itens):
        if limite and i >= limite:
            return
        valor = n.decimal(item.get("valorReembolsado"))
        if valor is None or item.get("id") is None:
            continue
        cod = n.inteiro(item.get("codSenador"))
        yield {
            "casa": CASA,
            "chave_fonte": str(item["id"]),
            "codigo_politico": cod,
            "nome_politico": n.texto(item.get("nomeSenador")),
            "ano": n.inteiro(item.get("ano")) or ano,
            "mes": n.inteiro(item.get("mes")) or 0,
            "categoria": n.texto(item.get("tipoDespesa")),
            "fornecedor": n.texto(item.get("fornecedor")),
            "cnpj_cpf": n.texto(item.get("cpfCnpj")),
            "data_documento": n.data(item.get("data")),
            "valor": valor,
            "url_documento": CEAPS_LINK.format(cod=cod, ano=ano) if cod else None,
        }


def coletar_despesas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    itens = client.get_json(CEAPS_URL.format(ano=ano))
    with sessao() as s:
        total = substituir_despesas(s, CASA, ano, _linhas_ceaps(itens, ano, limite))
    logger.info("Senado: %s despesas da cota gravadas em %s", total, ano)
    return total
