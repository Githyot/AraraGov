"""Fase 8: contratos dos municípios de todo o Brasil pelo PNCP.

O Portal Nacional de Contratações Públicas (Lei 14.133/2021, art. 174)
recebe os contratos de todos os entes. A API de consulta é aberta:

    https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD&pagina=N

Para cada município (fora de SP, que já vem do TCE-SP com mais detalhe),
grava `{ano}-contratos.md` no mesmo formato da fase 4:

- `contratos`: os maiores contratos do ano, com a emenda parlamentar
  quando o contrato informa que foi pago com uma.
- `obras`: contratos cujo objeto é obra do catálogo de custos. A quantidade
  vem dos itens da compra no PNCP (m², metro, unidade) e o valor por
  unidade é comparado com a faixa de referência do estado.
- `contratacoes-diretas`: empresas com 3 ou mais dispensas ou
  inexigibilidades no ano no mesmo município.

Contratos com pessoa física aparecem sem nome. Contratos anteriores à Lei
14.133 (e de quem ainda não publica no PNCP) não estão lá; o arquivo diz isso
na tabela `sem-dados`.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import md
from . import publicados
from .contratos import (COLUNAS_CONTRATOS, comparar, comparar_com_contratos, classificar, documento,
                        referencias_uf, unidade)
from .eleitos import COLUNAS_SEM_DADOS, municipios_ibge
from .tcesp import _resumir, formatar_cnpj, so_digitos

logger = logging.getLogger(__name__)

API = "https://pncp.gov.br/api/consulta/v1"
API_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
FONTE = "https://pncp.gov.br/app/contratos"
TAMANHO_PAGINA = 500
MODALIDADES_DIRETAS = {8: "Dispensa", 9: "Inexigibilidade"}
UFS_COM_TCE = {"SP", "RJ"}  # estes vêm do Tribunal de Contas, com mais detalhe
FORA_DO_TCE = {3304557}  # capital do RJ: fiscalizada pelo TCM-Rio, fica no PNCP

COLUNAS_CONTRATOS_PNCP = COLUNAS_CONTRATOS + ["emenda", "pncp"]


# O tamanho máximo da página muda de consulta para consulta (contratações
# recusam 500 com HTTP 400); o menor aceito por cada uma fica guardado aqui.
_TAMANHOS: Dict[str, int] = {}


def _pedir(client, caminho: str, params: Dict[str, Any], pagina: int) -> Any:
    import requests

    tamanho = _TAMANHOS.get(caminho, TAMANHO_PAGINA)
    while True:
        try:
            return client.get_json(f"{API}/{caminho}", {**params, "pagina": pagina, "tamanhoPagina": tamanho})
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 400 or tamanho <= 50:
                raise
            tamanho = 50
            _TAMANHOS[caminho] = tamanho
            logger.info("PNCP %s: página de %s registros", caminho, tamanho)


class PrazoEsgotado(Exception):
    pass


def _paginas(client, caminho: str, params: Dict[str, Any], prazo: Optional[float] = None) -> Iterator[Dict[str, Any]]:
    pagina = 1
    while True:
        if prazo is not None and time.monotonic() > prazo:
            raise PrazoEsgotado()
        dados = _pedir(client, caminho, params, pagina)
        for r in (dados or {}).get("data") or []:
            yield r
        if not dados or not dados.get("paginasRestantes"):
            return
        pagina += 1


# Pedidos ao mesmo tempo. O PNCP responde 429 quando são muitos; o cliente espera e tenta de novo.
TRABALHADORES = 4


def _em_paralelo(client, caminho: str, consultas: List[Dict[str, Any]], prazo: Optional[float] = None
                 ) -> Tuple[List[Dict[str, Any]], bool]:
    """Todas as páginas de cada consulta, várias consultas ao mesmo tempo.

    Devolve (linhas, completo). Com prazo, as consultas que não couberem nele
    ficam de fora e `completo` sai False.
    """
    def uma(params):
        linhas = []
        try:
            for r in _paginas(client, caminho, params, prazo):
                linhas.append(r)
        except PrazoEsgotado:
            return linhas, False
        except Exception as exc:  # noqa: BLE001 - uma semana fora do ar não derruba as outras
            logger.warning("PNCP %s %s: %s", caminho, params, exc)
            return linhas, False
        return linhas, True

    with ThreadPoolExecutor(max_workers=TRABALHADORES) as ex:
        resultados = list(ex.map(uma, consultas))
    return [r for linhas, _ in resultados for r in linhas], all(ok for _, ok in resultados)


def _janelas(inicio: date, fim: date, dias: int = 7) -> Iterator[Tuple[date, date]]:
    d = inicio
    while d <= fim:
        yield d, min(fim, d + timedelta(days=dias - 1))
        d += timedelta(days=dias)


def _compra(numero: Optional[str]) -> Optional[Tuple[str, int, int]]:
    """"83102277000152-1-000011/2025" -> (cnpj, ano, sequencial)."""
    m = re.fullmatch(r"(\d{14})-1-0*(\d+)/(\d{4})", (numero or "").strip())
    return (m.group(1), int(m.group(3)), int(m.group(2))) if m else None


def contratos(client, inicio: date, fim: date) -> List[Dict[str, Any]]:
    consultas = [{"dataInicial": a.strftime("%Y%m%d"), "dataFinal": b.strftime("%Y%m%d")} for a, b in _janelas(inicio, fim)]
    linhas, completo = _em_paralelo(client, "contratos", consultas)
    if not completo:
        logger.warning("PNCP: alguma semana de contratos não respondeu; os arquivos podem estar incompletos")
    return linhas


# As dispensas e inexigibilidades de todo o país são centenas de milhares por ano, e essa
# consulta só aceita páginas de 50. Sem limite de tempo ela ocupava a coleta inteira.
MINUTOS_DIRETAS = float(os.environ.get("ARARAGOV_PNCP_MINUTOS_DIRETAS", "60"))


def compras_diretas(client, inicio: date, fim: date, minutos: Optional[float] = None) -> Tuple[Dict[str, str], bool]:
    """Número de controle da compra -> modalidade, para dispensas e inexigibilidades municipais.

    Devolve também se a lista está completa (False quando o prazo acabou antes).
    """
    minutos = MINUTOS_DIRETAS if minutos is None else minutos
    prazo = time.monotonic() + minutos * 60
    saida: Dict[str, str] = {}
    completo = True
    for cod, nome in MODALIDADES_DIRETAS.items():
        consultas = [{"dataInicial": a.strftime("%Y%m%d"), "dataFinal": b.strftime("%Y%m%d"),
                      "codigoModalidadeContratacao": cod} for a, b in _janelas(inicio, fim)]
        linhas, ok = _em_paralelo(client, "contratacoes/publicacao", consultas, prazo)
        completo = completo and ok
        for r in linhas:
            if (r.get("orgaoEntidade") or {}).get("esferaId") == "M" and r.get("numeroControlePNCP"):
                amparo = (r.get("amparoLegal") or {}).get("nome")
                saida[r["numeroControlePNCP"]] = f"{nome}" + (f" ({amparo})" if amparo else "")
    if not completo:
        logger.warning("PNCP: prazo de %s min acabou ou o PNCP falhou; contratações diretas incompletas (%s)",
                       minutos, len(saida))
    return saida, completo


def agregar(linhas: Iterable[Dict[str, Any]], ano: int, diretas: Dict[str, str],
            ufs_fora: Iterable[str] = UFS_COM_TCE) -> Dict[int, Dict[str, Any]]:
    """IBGE -> {"uf", "municipio", "contratos", "obras", "diretas"}; só órgãos municipais."""
    fora = set(ufs_fora)
    por: Dict[int, Dict[str, Any]] = {}
    vistos = set()
    for r in linhas:
        if (r.get("orgaoEntidade") or {}).get("esferaId") != "M":
            continue
        un = r.get("unidadeOrgao") or {}
        uf = (un.get("ufSigla") or "").upper()
        try:
            ibge = int(un.get("codigoIbge") or 0)
        except ValueError:
            continue
        controle = r.get("numeroControlePNCP")
        if not ibge or (uf in fora and ibge not in FORA_DO_TCE) or controle in vistos or int(r.get("anoContrato") or 0) != ano:
            continue
        vistos.add(controle)
        m = por.setdefault(ibge, {"uf": uf, "municipio": un.get("municipioNome") or str(ibge), "contratos": [],
                                  "obras": [], "diretas": defaultdict(lambda: {"n": 0, "valor": Decimal(0), "fund": set(), "empresa": ""})})
        pj = (r.get("tipoPessoa") or "").upper() == "PJ"
        cnpj = so_digitos(r.get("niFornecedor")) if pj else ""
        valor = Decimal(str(r.get("valorGlobal") or r.get("valorInicial") or 0)).quantize(Decimal("0.01"))
        modalidade = diretas.get(r.get("numeroControlePncpCompra") or "")
        empresa = _resumir(r.get("nomeRazaoSocialFornecedor"), 120) if len(cnpj) == 14 else "Pessoa física (sem nome)"
        base = {
            "contrato": r.get("numeroContratoEmpenho") or controle,
            "cnpj": formatar_cnpj(cnpj) if len(cnpj) == 14 else None,
            "empresa": empresa,
            "orgao": _resumir(un.get("nomeUnidade") or (r.get("orgaoEntidade") or {}).get("razaoSocial"), 80),
            "modalidade": modalidade.split(" (")[0] if modalidade else None,
            "objeto": _resumir(r.get("objetoContrato")),
            "valor": valor,
        }
        m["contratos"].append({**base, "assinatura": r.get("dataAssinatura"),
                               "emenda": _resumir(str(r["emendaParlamentar"]), 80) if r.get("emendaParlamentar") else None,
                               "pncp": controle, "_compra": r.get("numeroControlePncpCompra")})
        item = classificar(r.get("objetoContrato") or "")
        if item:
            m["obras"].append({**base, "item": item, "_compra": r.get("numeroControlePncpCompra")})
        if modalidade and len(cnpj) == 14:
            d = m["diretas"][cnpj]
            d["n"] += 1
            d["valor"] += valor
            d["empresa"] = empresa
            d["fund"].add(_resumir(modalidade, 60))
    return por


def quantidade_dos_itens(client, numero_compra: Optional[str], unid_item: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Soma a quantidade dos itens da compra na unidade do item do catálogo."""
    compra = _compra(numero_compra)
    if not compra:
        return None, None
    cnpj, ano, seq = compra
    try:
        itens = client.get_json(API_ITENS.format(cnpj=cnpj, ano=ano, seq=seq), {"pagina": 1, "tamanhoPagina": 100}) or []
    except Exception as e:  # noqa: BLE001 - sem itens, fica sem quantidade
        logger.debug("Itens de %s indisponíveis: %s", numero_compra, e)
        return None, None
    total = Decimal(0)
    for it in itens if isinstance(itens, list) else []:
        if unidade(str(it.get("unidadeMedida") or "")) == unid_item:
            total += Decimal(str(it.get("quantidade") or 0))
    return (total, unid_item) if total > 0 else (None, None)


def completar_obras(client, por: Dict[int, Dict[str, Any]], ano: int, saida: Path, unidades_itens: Dict[str, str],
                    limite_itens: int) -> int:
    refs_por_uf: Dict[str, Dict] = {}
    pedidos = 0
    for m in por.values():
        refs = refs_por_uf.setdefault(m["uf"], referencias_uf(saida, m["uf"]))
        for o in sorted(m["obras"], key=lambda o: -o["valor"]):
            unid_item = unidades_itens.get(o["item"])
            qtd, unid = (None, None)
            if unid_item and pedidos < limite_itens:
                qtd, unid = quantidade_dos_itens(client, o.get("_compra"), unid_item)
                pedidos += 1
            o.update({"quantidade": qtd, "unidade": unid})
            o.update(comparar(o["item"], unid, qtd or Decimal(0), o["valor"], refs, ano, unidades_itens))
    # Itens sem faixa publicada: faixa dos contratos do mesmo estado.
    por_uf: Dict[str, Dict] = defaultdict(dict)
    for ibge, m in por.items():
        por_uf[m["uf"]][ibge] = m
    for grupo in por_uf.values():
        comparar_com_contratos(grupo, ano, unidades_itens)
    return pedidos


def gerar(client, saida: Path, anos: Iterable[int], hoje: Optional[date] = None, dias: Optional[int] = None,
          limite_itens: int = 3000) -> int:
    """`dias` limita a busca aos primeiros N dias do ano (teste)."""
    from .custos import carregar_itens

    hoje = hoje or date.today()
    unidades_itens = {i.id: i.unidade for i in carregar_itens().values()}
    nomes = {cod: nome for (_, _), (cod, nome) in municipios_ibge().items()}
    total = 0
    for ano in sorted(anos):
        if not dias:
            reaproveitados = _ano_ja_publicado(client, saida, ano, hoje)
            if reaproveitados:
                total += reaproveitados
                continue
        inicio = date(ano, 1, 1)
        fim = min(date(ano, 12, 31), hoje - timedelta(days=1))
        if dias:
            fim = min(fim, inicio + timedelta(days=dias - 1))
        diretas, diretas_completas = compras_diretas(client, inicio, fim)
        por = agregar(contratos(client, inicio, fim), ano, diretas)
        pedidos = completar_obras(client, por, ano, saida, unidades_itens, limite_itens)
        for ibge, m in por.items():
            for lista in (m["contratos"], m["obras"]):
                for r in lista:
                    r.pop("_compra", None)
            mun = nomes.get(ibge, m["municipio"])
            caminho = saida / "v1" / "municipios" / m["uf"].lower() / str(ibge) / f"{ano}-contratos.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            texto = documento(ibge, mun, ano, m, hoje, uf=m["uf"], fonte=FONTE, colunas_contratos=COLUNAS_CONTRATOS_PNCP)
            caminho.write_text(_com_sem_dados(texto, hoje, diretas_completas), encoding="utf-8")
            total += 1
        logger.info("PNCP %s: %s municípios, %s compras diretas, %s consultas de itens", ano, len(por), len(diretas), pedidos)
    return total


def _ano_ja_publicado(client, saida: Path, ano: int, hoje: date) -> int:
    """Ano fechado: copia os contratos já publicados (fora dos estados que vêm do tribunal)."""
    if os.environ.get("ARARAGOV_REAPROVEITAR") != "1" or not publicados.ano_fechado(ano, hoje):
        return 0
    por_uf: Dict[str, List[int]] = defaultdict(list)
    for (uf, _), (cod, _) in municipios_ibge().items():
        if uf not in UFS_COM_TCE or cod in FORA_DO_TCE:
            por_uf[uf].append(cod)
    return sum(publicados.reaproveitar(client, saida, uf, cods, f"{ano}-contratos.md") for uf, cods in sorted(por_uf.items()))


def _com_sem_dados(texto: str, hoje: date, diretas_completas: bool = True) -> str:
    """Acrescenta a tabela sem-dados sobre o que o PNCP não cobre."""
    doc = md.ler(texto)
    tabelas = dict(doc.tabelas)
    tabelas["sem-dados"] = [{
        "secao": "contratos", "esfera": "municipal", "responsavel": "Prefeitura",
        "motivo": "Só aparecem os contratos que a prefeitura publicou no PNCP. Contratos pela lei antiga "
                  "(8.666) e quem ainda não publica ficam de fora.",
        "obrigacao": "Lei 14.133/2021, art. 94 e 174", "fonte_consultada": FONTE, "consultado_em": hoje.isoformat(),
    }]
    if not diretas_completas:
        tabelas["sem-dados"].append({
            "secao": "contratacoes-diretas", "esfera": "municipal", "responsavel": "AraraGov",
            "motivo": "Nesta coleta não deu tempo de ler todas as dispensas e inexigibilidades do país no PNCP; "
                      "a lista de contratações diretas pode estar incompleta.",
            "obrigacao": "", "fonte_consultada": FONTE, "consultado_em": hoje.isoformat(),
        })
    colunas = dict(doc.colunas)
    colunas["sem-dados"] = COLUNAS_SEM_DADOS
    titulo = next((l[2:] for l in texto.splitlines() if l.startswith("# ")), None)
    return md.escrever(doc.meta, tabelas, colunas=colunas, titulo=titulo, textos={
        "obras": "## Obras e o custo de referência\n\nValor por unidade do contrato (quantidade pelos itens da "
        "compra no PNCP) comparado com a faixa de referência do estado. Acima da faixa não quer dizer "
        "irregular: é um ponto para perguntar.",
        "contratos": "## Maiores contratos do ano",
        "contratacoes-diretas": "## Mesma empresa com várias contratações diretas",
        "sem-dados": "## O que ainda não há",
    })
