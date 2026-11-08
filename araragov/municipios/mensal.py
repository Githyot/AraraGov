"""Arrecadação e gastos de cada mês, pela Matriz de Saldos Contábeis (MSC).

A declaração anual (DCA, `financas.py`) só sai em abril do ano seguinte. A
MSC é entregue todo mês ao Tesouro Nacional (Portaria STN 642/2019) e a API
do Siconfi publica a movimentação do mês (`id_tv=period_change`) de cada
conta, com a natureza da receita e a função da despesa.

Contas usadas (Plano de Contas Aplicado ao Setor Público, classe 6):

- 6.2.1.2 receita realizada, menos 6.2.1.3 deduções (Fundeb, restituições);
- 6.2.2.1.3.04 crédito empenhado liquidado pago.

Saldo credor soma e devedor subtrai. Para cada município e ano é gravado
`v1/municipios/{uf}/{ibge}/{ano}-mensal.md`. Os meses fechados há mais de
três meses vêm da publicação anterior; só os recentes são buscados de novo.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .. import normalizar as n
from . import md
from .financas import PUBLICADO, SICONFI, SICONFI_SITE, Ente, _paginar, entes_municipais

logger = logging.getLogger(__name__)

RECEITA_REALIZADA = "6212"
DEDUCOES = "6213"
PAGO = "6221304"

# Funções de governo (Portaria MOG 42/1999).
FUNCOES = {
    "01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "05": "Defesa Nacional", "06": "Segurança Pública", "07": "Relações Exteriores",
    "08": "Assistência Social", "09": "Previdência Social", "10": "Saúde", "11": "Trabalho",
    "12": "Educação", "13": "Cultura", "14": "Direitos da Cidadania", "15": "Urbanismo",
    "16": "Habitação", "17": "Saneamento", "18": "Gestão Ambiental", "19": "Ciência e Tecnologia",
    "20": "Agricultura", "21": "Organização Agrária", "22": "Indústria", "23": "Comércio e Serviços",
    "24": "Comunicações", "25": "Energia", "26": "Transporte", "27": "Desporto e Lazer",
    "28": "Encargos Especiais", "99": "Reserva de Contingência",
}

COLUNAS_MESES = ["mes", "arrecadado", "impostos", "repasses", "outras", "gasto"]
COLUNAS_AREAS_MES = ["mes", "funcao", "area", "pago"]

# Meses mais novos que isto são buscados de novo: a prefeitura pode retificar.
MESES_ABERTOS = 3


def grupo(natureza: Optional[str]) -> str:
    """Origem da receita pelos dois primeiros dígitos da natureza."""
    p = str(natureza or "")[:2]
    if p == "11":
        return "impostos"
    if p in ("17", "24"):
        return "repasses"
    return "outras"


def _sinal(item: Dict[str, Any]) -> Decimal:
    v = n.decimal(item.get("valor")) or Decimal(0)
    return v if str(item.get("natureza_conta", "")).upper() == "C" else -v


def resumo_mes(itens: List[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Decimal], Dict[str, Decimal]]]:
    """(totais do mês, pago por função) ou `None` se o mês não foi entregue."""
    if not itens:
        return None
    totais = {"impostos": Decimal(0), "repasses": Decimal(0), "outras": Decimal(0), "gasto": Decimal(0)}
    funcoes: Dict[str, Decimal] = defaultdict(Decimal)
    for item in itens:
        conta = str(item.get("conta_contabil") or "")
        if conta.startswith((RECEITA_REALIZADA, DEDUCOES)):
            # Deduções são conta redutora: o saldo devedor diminui a receita.
            totais[grupo(item.get("natureza_receita"))] += _sinal(item)
        elif conta.startswith(PAGO):
            v = _sinal(item)
            totais["gasto"] += v
            funcoes[str(item.get("funcao") or "").zfill(2)] += v
    totais["arrecadado"] = totais["impostos"] + totais["repasses"] + totais["outras"]
    return totais, dict(funcoes)


def documento(ente: Ente, ano: int, meses: Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]], hoje: date) -> str:
    linhas_meses, linhas_areas = [], []
    for mes in sorted(meses):
        totais, funcoes = meses[mes]
        linhas_meses.append({"mes": mes, **{k: totais[k] for k in COLUNAS_MESES if k != "mes"}})
        for f in sorted(funcoes):
            if funcoes[f]:
                linhas_areas.append({"mes": mes, "funcao": f, "area": FUNCOES.get(f, f"Função {f}"), "pago": funcoes[f]})
    meta = {
        "tipo": "municipio-mensal", "ibge": ente.ibge, "municipio": ente.nome, "uf": ente.uf, "ano": ano,
        "populacao": ente.populacao, "atualizado": hoje,
        "fonte": f"{SICONFI_SITE} (Matriz de Saldos Contábeis, movimento do mês)",
    }
    return md.escrever(
        {k: v for k, v in meta.items() if v is not None},
        {"meses": linhas_meses, "areas-mes": linhas_areas},
        colunas={"meses": COLUNAS_MESES, "areas-mes": COLUNAS_AREAS_MES},
        titulo=f"{ente.nome} ({ente.uf}), {ano}, mês a mês",
        textos={
            "meses": "## Meses\n\nArrecadado é a receita realizada menos as deduções (como a parte "
            "que vai para o Fundeb); gasto é o que foi pago no mês.",
            "areas-mes": "## Pago por área em cada mês",
        },
    )


def _ler_publicado(client, ente: Ente, ano: int) -> Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Meses do arquivo já publicado no GitHub Pages, se houver."""
    try:
        url = f"{PUBLICADO}/v1/municipios/{ente.uf.lower()}/{ente.ibge}/{ano}-mensal.md"
        doc = md.ler(client.get_bytes(url).decode("utf-8"))
    except Exception:
        return {}
    meses: Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for r in doc.tabelas.get("meses", []):
        mes = n.inteiro(r.get("mes"))
        if mes:
            meses[mes] = ({k: r.get(k) for k in COLUNAS_MESES if k != "mes"}, {})
    for r in doc.tabelas.get("areas-mes", []):
        mes = n.inteiro(r.get("mes"))
        if mes in meses and r.get("funcao"):
            meses[mes][1][str(r["funcao"])] = r.get("pago")
    return meses


def meses_possiveis(ano: int, hoje: date) -> List[int]:
    """Meses já terminados do ano (a MSC do mês sai até o fim do mês seguinte)."""
    if ano < hoje.year:
        return list(range(1, 13))
    return list(range(1, hoje.month))


def aberto(ano: int, mes: int, hoje: date) -> bool:
    return (hoje.year - ano) * 12 + hoje.month - mes <= MESES_ABERTOS


def gerar(
    novo_cliente: Callable[[], Any],
    saida: Path,
    anos: Iterable[int],
    ufs: Iterable[str],
    hoje: Optional[date] = None,
    limite: Optional[int] = None,
    trabalhadores: int = 4,
    reaproveitar: bool = True,
) -> Dict[str, int]:
    """Grava o `{ano}-mensal.md` de cada município. `limite` é o máximo de
    pedidos município-mês ao Siconfi nesta execução; o resto fica para a próxima."""
    hoje = hoje or date.today()
    principal = novo_cliente()
    entes = entes_municipais(principal, ufs)
    pares = [(e, a) for a in sorted(set(anos), reverse=True) for e in entes]
    contagem = {"meses_siconfi": 0, "meses_reaproveitados": 0, "arquivos": 0}
    trava = threading.Lock()
    orcamento = [limite if limite is not None else 10 ** 9]
    local = threading.local()

    def cliente():
        if not hasattr(local, "c"):
            local.c = novo_cliente()
        return local.c

    def processar(par: Tuple[Ente, int]) -> None:
        ente, ano = par
        c = cliente()
        meses = _ler_publicado(c, ente, ano) if reaproveitar else {}
        reaproveitados = 0
        for mes in meses_possiveis(ano, hoje):
            if mes in meses and not aberto(ano, mes, hoje):
                reaproveitados += 1
                continue
            with trava:
                pode = orcamento[0] > 0
                if pode:
                    orcamento[0] -= 1
            if not pode:
                break
            try:
                itens = _paginar(c, f"{SICONFI}/msc_orcamentaria", {
                    "id_ente": ente.ibge, "an_referencia": ano, "me_referencia": mes,
                    "co_tipo_matriz": "MSCC", "classe_conta": 6, "id_tv": "period_change",
                })
            except Exception as erro:  # um município fora do ar não para a coleta
                logger.warning("MSC %s %s-%02d: %s", ente.ibge, ano, mes, erro)
                continue
            r = resumo_mes(itens)
            if r is not None:
                meses[mes] = r
                with trava:
                    contagem["meses_siconfi"] += 1
        with trava:
            contagem["meses_reaproveitados"] += reaproveitados
        if meses:
            caminho = saida / "v1" / "municipios" / ente.uf.lower() / str(ente.ibge) / f"{ano}-mensal.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(documento(ente, ano, meses, hoje), encoding="utf-8")
            with trava:
                contagem["arquivos"] += 1

    if trabalhadores <= 1:
        for par in pares:
            processar(par)
    else:
        with ThreadPoolExecutor(trabalhadores) as pool:
            list(pool.map(processar, pares))
    logger.info("MSC mensal: %s municípios, anos %s: %s meses do Siconfi, %s reaproveitados, %s arquivos",
                len(entes), sorted(set(anos)), contagem["meses_siconfi"], contagem["meses_reaproveitados"],
                contagem["arquivos"])
    return contagem
