"""Pagamentos de prefeituras que usam o portal de transparência Agili (IPM).

Cerca de cem prefeituras e câmaras, quase todas do Mato Grosso, publicam o
portal da transparência na AgiliCloud. Todas respondem pela mesma API JSON:

- `GET  {API}/seletor/get` lista os clientes (prefeituras, câmaras, consórcios);
- `POST {API}/contabilidade/despesas/empenhosporexercicio/...` devolve os
  empenhos do ano, página a página, com órgão, função, subfunção, natureza da
  despesa, favorecido (CPF ou CNPJ) e os valores empenhado, liquidado e pago.

O cabeçalho `uc` escolhe a prefeitura. O formato do pedido veio do projeto
"Transparência Cidadã - Portal de Empenhos" (Lucas7X7, licença MIT,
github.com/Lucas7X7/transparencia-cidada-portal-de-empenhos).

As linhas são traduzidas para os campos do TCE-SP e somadas por
`tcesp.agregar`, para sair no mesmo `{uf}/{ibge}/{ano}-pagamentos.md`. CPF
nunca é gravado: pessoas físicas entram só no total.
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import publicados
from . import tcesp
from .eleitos import chave_nome, municipios_ibge
from .tcepb import cnpj_valido
from .tcesp import ELEMENTO_OBRAS, PAGO, so_digitos

logger = logging.getLogger(__name__)

API = "https://transparencia.agilicloud.com.br/api"
GRID = (API + "/contabilidade/despesas/empenhosporexercicio/obterdadosempenhosporexercicio/"
        "?model=Agili.Blue.Portal.Shared.Contabilidade.Dto.Despesas.EmpenhosPorExercicio.EmpenhosPorExercicioGridDto"
        "&page={pagina}&size={tamanho}&withCount=true")
DETALHE = API + "/contabilidade/contabilidade/obterDadosAbaDadosDetalhadosDespesa?idEmpenho={id}"
TAMANHO_PAGINA = 1000
# Histórico das obras: um pedido por empenho, então só para as maiores.
MAX_DETALHES = 100
TRIBUNAL = "portal da transparência da prefeitura (Agili/IPM)"

_PREFIXO = re.compile(r"^\s*[\d.]+\s*-\s*")
_PREFEITURA = re.compile(r"^(PREFEITURA|MUNICIPIO|MUNICÍPIO)( MUNICIPAL)?( DE| DO| DA| DOS| DAS)?\s+", re.I)


def _corpo(ano: int) -> List[Dict[str, Any]]:
    """Filtros do grid "Empenhos por exercício" (o portal exige a lista inteira)."""
    def campo(nome, rotulo, tipo, tipo_param, operador=1, valor=None, **extra):
        c = {"field": nome, "label": rotulo, "nameFieldTable": extra.pop("tabela", ""),
             "aliasTable": extra.pop("alias", "E"), "type": tipo, "typeParam": tipo_param,
             "operatorDefault": operador, "operatorValue": operador, "checked": True,
             "order": extra.pop("ordem", 0), "required": extra.pop("obrigatorio", False)}
        if valor is not None:
            c["value"] = valor
        c.update(extra)
        return c

    return [
        campo("IdUnidadeGestora", "Unidade gestora", 8, 1, tabela="Id", alias="UG", ordem=10),
        campo("IdEstrutFonteRecurso", "Fonte dos recursos", 8, 1, tabela="IdEstrutFonteRecurso", ordem=25),
        campo("DataInicio", "De", 3, 3, valor=f"{ano}-01-01", tabela="DataEmpenho", ordem=50,
              valueFinnaly=f"{ano}-12-31"),
        campo("DataFim", "Até", 3, 3, valor=f"{ano}-12-31", tabela="DataEmpenho", ordem=50),
        campo("FiltroExercicio", "Exercício", 1, 1, valor=str(ano), ordem=100, obrigatorio=True),
        campo("Favorecido", "Favorecido", 2, 2, operador=12, valor="", ordem=120, valueToReplace=".;-;/"),
        campo("IdFundo", "Fundo", 8, 1, alias="DO", ordem=130),
        campo("IdClassificacaoDespesa", "Classificação da despesa", 9, 1, ordem=140),
        campo("IdNaturezaDespesa", "Natureza de despesa", 8, 1, tabela="Id", alias="ND", ordem=1000),
    ]


def _nome_municipio(c: Dict[str, Any]) -> str:
    m = c.get("municipio")
    if isinstance(m, dict):
        m = m.get("nome") or m.get("descricao")
    if m:
        return str(m)
    return _PREFEITURA.sub("", str(c.get("nomeRazaoSocial") or "")).split(" - ")[0]


def prefeituras(client) -> List[Tuple[str, int, str]]:
    """(uf, ibge, shortname) das prefeituras atendidas pela AgiliCloud."""
    ibge = municipios_ibge()
    saida, vistos = [], set()
    for c in client.get_json(f"{API}/seletor/get") or []:
        curto = str(c.get("shortname") or "").strip()
        if not curto.lower().startswith("pref"):
            continue  # câmaras, consórcios e institutos de previdência ficam de fora
        uf = str(c.get("uf") or "").strip().upper()
        achado = ibge.get((uf, chave_nome(_nome_municipio(c))))
        if not achado:
            logger.info("AgiliCloud: %s (%s) sem código IBGE, fica de fora", curto, uf)
            continue
        if achado[0] in vistos:
            continue
        vistos.add(achado[0])
        saida.append((uf, achado[0], curto))
    return sorted(saida)


def empenhos(client, curto: str, ano: int, tamanho: Optional[int] = None,
             limite: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    tamanho = tamanho or TAMANHO_PAGINA
    cab = {"uc": curto, "Content-Type": "application/json; charset=utf-8"}
    pagina, lidos = 0, 0
    while True:
        dados = client.pedir_json("POST", GRID.format(pagina=pagina, tamanho=tamanho), _corpo(ano), cab) or {}
        linhas = dados.get("data") or []
        for linha in linhas:
            yield linha
            lidos += 1
            if limite is not None and lidos >= limite:
                return
        pagina += 1
        if not linhas or pagina * tamanho >= int(dados.get("totalResult") or 0):
            return


def _sem_codigo(texto: Any) -> str:
    """'10 - Saúde' -> 'Saúde'."""
    return _PREFIXO.sub("", str(texto or "")).strip()


def _brl(v: Any) -> str:
    """Número da API (1234.5) no formato que tcesp.valor lê ('1234,50')."""
    try:
        return f"{float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "0"


def traduzir(rs: Iterable[Dict[str, Any]], cod: int, nome: str) -> Iterator[Dict[str, str]]:
    """Empenho da Agili -> linha no formato do TCE-SP (só o valor pago)."""
    for r in rs:
        doc = so_digitos(r.get("cpfcnpjFavorecido"))
        pj = cnpj_valido(doc)
        yield {
            "tp_despesa": PAGO,
            "codigo_municipio_ibge": str(cod),
            "ds_municipio": nome,
            "vl_despesa": _brl(r.get("pago")),
            "ds_elemento": f"{so_digitos(r.get('naturezaDespesa'))} - {r.get('elementoDespesa') or ''}",
            "tp_identificador_despesa": "CNPJ" if pj else "CPF",
            # Pessoa física (ou CPF mascarado): só um marcador; tcesp guarda só um hash.
            "nr_identificador_despesa": doc if pj else doc[-11:],
            "ds_despesa": r.get("nomeFavorecido") or "",
            "ds_funcao_governo": _sem_codigo(r.get("funcao")),
            "ds_subfuncao_governo": _sem_codigo(r.get("subfuncao")),
            "ds_orgao": _sem_codigo(r.get("orgao")),
            "nr_empenho": str(r.get("numeroAno") or ""),
            "ds_acao": "",
            "historico_despesa": "",
            "_id": str(r.get("id") or ""),
        }


# Falhas do pedido de histórico nesta execução; depois de algumas, para de pedir
# (cada falha custa as novas tentativas do cliente, cerca de um minuto).
_falhas_detalhe: List[str] = []
MAX_FALHAS_DETALHE = 3


def _historicos(client, curto: str, m: tcesp.Municipio, ids: Dict[Tuple[str, str], str]) -> None:
    """Preenche o histórico das maiores obras (um pedido por empenho)."""
    maiores = sorted(m.obras.items(), key=lambda kv: kv[1]["pago"], reverse=True)[:MAX_DETALHES]
    for chave, obra in maiores:
        i = ids.get(chave)
        if not i or len(_falhas_detalhe) >= MAX_FALHAS_DETALHE:
            continue
        try:
            d = client.pedir_json("GET", DETALHE.format(id=i), None, {"uc": curto}) or {}
        except Exception as exc:  # noqa: BLE001 - sem histórico, a obra continua no arquivo
            logger.info("AgiliCloud %s: sem histórico do empenho %s (%s)", curto, i, exc)
            _falhas_detalhe.append(curto)
            break
        obra["historico"] = tcesp._resumir(d.get("historico"))


def _um_municipio(client, saida: Path, uf: str, cod: int, curto: str, nome: str, ano: int, hoje: date,
                  limite: Optional[int]) -> bool:
    ids: Dict[Tuple[str, str], str] = {}

    def linhas():
        for l in traduzir(empenhos(client, curto, ano, limite=limite), cod, nome):
            if so_digitos(l["ds_elemento"]).startswith(ELEMENTO_OBRAS):
                ids[(l["ds_orgao"].strip(), l["nr_empenho"].strip())] = l["_id"]
            yield l

    try:
        municipios = tcesp.agregar(linhas())
    except Exception as exc:  # noqa: BLE001 - um portal fora do ar não para os outros
        logger.warning("AgiliCloud %s %s: %s", curto, ano, exc)
        return False
    m = municipios.get(cod)
    if not m:
        logger.info("AgiliCloud %s %s: nenhum empenho", curto, ano)
        return False
    m.nome = nome
    _historicos(client, curto, m, ids)
    caminho = saida / "v1" / "municipios" / uf.lower() / str(cod) / f"{ano}-pagamentos.md"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fonte = f"https://{curto}.agilicloud.com.br/"
    caminho.write_text(tcesp.documento(cod, ano, m, hoje, tcesp._governo(saida, cod, ano, uf), uf=uf,
                                       fonte=fonte, tribunal=TRIBUNAL), encoding="utf-8")
    return True


def gerar(client, saida: Path, anos: Iterable[int], limite_municipios: Optional[int] = None,
          limite_linhas: Optional[int] = None, hoje: Optional[date] = None, trabalhadores: int = 4) -> int:
    """Gera `{uf}/{ibge}/{ano}-pagamentos.md` das prefeituras da AgiliCloud.

    Um pedido por vez em cada portal, poucos portais ao mesmo tempo: o
    servidor é um só para todas as prefeituras.
    """
    hoje = hoje or date.today()
    nomes = {cod: nome for (_, _), (cod, nome) in municipios_ibge().items()}
    lista = prefeituras(client)[:limite_municipios]
    logger.info("AgiliCloud: %s prefeituras", len(lista))
    total = 0
    for ano in sorted(anos):
        pendentes = []
        for uf, cod, curto in lista:
            # Ano fechado já publicado: só copia (o portal não muda mais esse ano).
            if (os.environ.get("ARARAGOV_REAPROVEITAR") == "1" and publicados.ano_fechado(ano, hoje)
                    and publicados.reaproveitar(client, saida, uf, [cod], f"{ano}-pagamentos.md", 1)):
                total += 1
                continue
            pendentes.append((uf, cod, curto))
        with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
            feitos = sum(ex.map(lambda p: _um_municipio(client, saida, p[0], p[1], p[2], nomes.get(p[1], p[2]),
                                                        ano, hoje, limite_linhas), pendentes))
        logger.info("AgiliCloud %s: %s de %s prefeituras", ano, feitos, len(pendentes))
        total += feitos
    return total
