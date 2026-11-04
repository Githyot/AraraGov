"""Câmara dos Deputados.

Fontes (dados abertos, sem chave):
- Deputados: API REST /api/v2/deputados (com foto, partido e UF).
- Votações e votos: arquivos anuais em massa de dadosabertos.camara.leg.br/arquivos.
  Um download por ano em vez de milhares de chamadas à API.
- Cota parlamentar (CEAP): arquivo anual camara.leg.br/cotas/Ano-{ano}.csv.zip.
  A API REST de despesas devolve vazio desde 2026 (documentado pelo projeto
  Mamute Político), por isso usamos o arquivo em massa.
"""

from __future__ import annotations

import io
import logging
import zipfile
from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterator, List, Optional

from ..db import sessao
from ..http import HttpClient
from .. import normalizar as n
from ._comum import gravar_politico, gravar_votacao, ler_csv, substituir_despesas

logger = logging.getLogger(__name__)

API = "https://dadosabertos.camara.leg.br/api/v2"
ARQUIVOS = "https://dadosabertos.camara.leg.br/arquivos"
CEAP_URL = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
CASA = "camara"


def legislatura_pela_data(hoje: Optional[date] = None) -> int:
    """A 57ª legislatura começou em 1º/fev/2023; cada uma dura 4 anos."""
    hoje = hoje or date.today()
    ano = hoje.year - (1 if hoje.month == 1 else 0)
    return 57 + (ano - 2023) // 4


def legislatura_atual(client: HttpClient) -> int:
    try:
        dados = client.get_json(f"{API}/legislaturas", {"ordem": "DESC", "ordenarPor": "id", "itens": 1})
        return int(dados["dados"][0]["id"])
    except Exception:  # a API às vezes responde 504; a legislatura é previsível
        legislatura = legislatura_pela_data()
        logger.warning("API de legislaturas indisponível; usando a %sª pela data", legislatura)
        return legislatura


def coletar_deputados(client: HttpClient, legislatura: Optional[int] = None) -> int:
    """Grava todos os deputados da legislatura (inclusive quem já saiu) e
    marca quem está em exercício hoje."""
    legislatura = legislatura or legislatura_atual(client)
    todos = _paginar(client, f"{API}/deputados", {"idLegislatura": legislatura, "itens": 100})
    em_exercicio = {d["id"] for d in _paginar(client, f"{API}/deputados", {"itens": 100})}
    with sessao() as s:
        for d in todos:
            gravar_politico(
                s,
                {
                    "casa": CASA,
                    "cargo": "Deputado Federal",
                    "codigo": int(d["id"]),
                    "nome": n.texto(d.get("nome")) or str(d["id"]),
                    "partido": n.texto(d.get("siglaPartido")),
                    "uf": n.texto(d.get("siglaUf")),
                    "url_foto": n.texto(d.get("urlFoto")),
                    "email": n.texto(d.get("email")),
                    "legislatura": legislatura,
                    "em_exercicio": d["id"] in em_exercicio,
                },
            )
    logger.info("Câmara: %s deputados gravados (legislatura %s)", len(todos), legislatura)
    return len(todos)


def _paginar(client: HttpClient, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    pagina = 1
    while True:
        dados = client.get_json(url, {**params, "pagina": pagina})
        itens.extend(dados.get("dados") or [])
        if not any(l.get("rel") == "next" for l in dados.get("links") or []):
            return itens
        pagina += 1


def coletar_votacoes(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    """Grava as votações nominais do ano (as simbólicas não têm votos
    individuais e ficam de fora)."""

    def baixar(nome: str) -> Iterator[Dict[str, str]]:
        return ler_csv(client.get_bytes(f"{ARQUIVOS}/{nome}/csv/{nome}-{ano}.csv"))

    votos_por_votacao: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for linha in baixar("votacoesVotos"):
        codigo = n.inteiro(linha.get("deputado_id"))
        if codigo is None:
            continue
        votos_por_votacao[linha["idVotacao"]].append(
            {
                "casa": CASA,
                "codigo_politico": codigo,
                "nome_politico": n.texto(linha.get("deputado_nome")),
                "partido": n.texto(linha.get("deputado_siglaPartido")),
                "uf": n.texto(linha.get("deputado_siglaUf")),
                "voto_original": n.texto(linha.get("voto")),
                "voto": n.voto(linha.get("voto")),
            }
        )

    proposicoes: Dict[str, Dict[str, str]] = {}
    for linha in baixar("votacoesProposicoes"):
        proposicoes.setdefault(linha["idVotacao"], linha)

    orientacoes: Dict[str, Dict[str, str]] = defaultdict(dict)
    for linha in baixar("votacoesOrientacoes"):
        bancada = n.texto(linha.get("siglaBancada"))
        if bancada:
            orientacoes[linha["idVotacao"]][bancada] = n.texto(linha.get("orientacao")) or ""

    gravadas = 0
    with sessao() as s:
        for linha in baixar("votacoes"):
            vid = linha["id"]
            votos = votos_por_votacao.get(vid)
            if not votos:
                continue
            prop = proposicoes.get(vid, {})
            ident = None
            if prop.get("proposicao_siglaTipo"):
                ident = f"{prop['proposicao_siglaTipo']} {prop.get('proposicao_numero')}/{prop.get('proposicao_ano')}"
            prop_id = n.texto(prop.get("proposicao_id"))
            aprovacao = n.texto(linha.get("aprovacao"))
            gravar_votacao(
                s,
                {
                    "id": f"{CASA}:{vid}",
                    "casa": CASA,
                    "codigo": vid,
                    "data": n.data_hora(linha.get("dataHoraRegistro")) or n.data_hora(linha.get("data")),
                    "orgao": n.texto(linha.get("siglaOrgao")),
                    "descricao": n.texto(linha.get("descricao")),
                    "proposicao": ident,
                    "ementa": n.texto(prop.get("proposicao_ementa")),
                    "resultado": {"1": "Aprovada", "0": "Rejeitada"}.get(aprovacao or "", aprovacao),
                    "link": (
                        f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
                        if prop_id
                        else None
                    ),
                    "orientacoes": orientacoes.get(vid) or None,
                },
                votos,
            )
            gravadas += 1
            if limite and gravadas >= limite:
                break
    logger.info("Câmara: %s votações nominais gravadas em %s", gravadas, ano)
    return gravadas


def _linhas_ceap(conteudo_zip: bytes, ano: int, limite: Optional[int]) -> Iterator[Dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
        nome = next(x for x in z.namelist() if x.lower().endswith(".csv"))
        conteudo = z.read(nome)
    for i, linha in enumerate(ler_csv(conteudo)):
        if limite and i >= limite:
            return
        valor = n.decimal(linha.get("vlrLiquido"))
        if valor is None:
            continue
        documento = (linha.get("ideDocumento") or "").strip()
        if documento and documento != "0":
            chave = ":".join([documento, linha.get("numSubCota") or "0", linha.get("numParcela") or "0"])
        else:  # sem id de documento: chave pelos campos que identificam o gasto
            chave = "sem-doc:" + ":".join(
                linha.get(c) or ""
                for c in ("ideCadastro", "txtCNPJCPF", "txtNumero", "datEmissao", "vlrLiquido", "numMes", "numParcela")
            )
        yield {
            "casa": CASA,
            "chave_fonte": chave,
            "codigo_politico": n.inteiro(linha.get("ideCadastro")),
            "nome_politico": n.texto(linha.get("txNomeParlamentar")),
            "ano": n.inteiro(linha.get("numAno")) or ano,
            "mes": n.inteiro(linha.get("numMes")) or 0,
            "categoria": n.texto(linha.get("txtDescricao")),
            "fornecedor": n.texto(linha.get("txtFornecedor")),
            "cnpj_cpf": n.texto(linha.get("txtCNPJCPF")),
            "data_documento": n.data(linha.get("datEmissao")),
            "valor": valor,
            "url_documento": n.texto(linha.get("urlDocumento")),
        }


def coletar_despesas(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    conteudo = client.get_bytes(CEAP_URL.format(ano=ano))
    with sessao() as s:
        total = substituir_despesas(s, CASA, ano, _linhas_ceap(conteudo, ano, limite))
    logger.info("Câmara: %s despesas da cota gravadas em %s", total, ano)
    return total
