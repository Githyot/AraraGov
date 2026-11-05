"""Arrecadação e gastos por área, pelo Siconfi (fase 2 de docs/municipios.md).

Cada município entrega ao Tesouro Nacional, até 30 de abril do ano seguinte,
a Declaração de Contas Anuais (DCA, LRF art. 51). A API do Siconfi publica:

- Anexo I-C: receitas orçamentárias (bruta e deduções) por conta.
- Anexo I-E: despesas por função (saúde, educação…) e subfunção, nas fases
  empenhada, liquidada e paga.

Para cada município e ano é gravado `v1/municipios/{uf}/{ibge}/{ano}.md`.
São 5.570 municípios; a coleta busca no Siconfi só o que falta ou pode ter
mudado (os dois últimos anos) e reaproveita os anos fechados já publicados,
como a coleta federal faz com o histórico.
"""

from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .. import normalizar as n
from ..collectors.referencia import IPCA_URL
from . import md

logger = logging.getLogger(__name__)

SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
SICONFI_SITE = "https://siconfi.tesouro.gov.br"
PUBLICADO = "https://githyot.github.io/AraraGov"
ANEXO_RECEITAS = "DCA-Anexo I-C"
ANEXO_FUNCOES = "DCA-Anexo I-E"

COLUNA_BRUTA = "receitas brutas realizadas"
FASES = {
    "despesas empenhadas": "empenhado",
    "despesas liquidadas": "liquidado",
    "despesas pagas": "pago",
}

# Destaques de arrecadação que a população conhece pelo nome. Cada um usa a
# conta mais geral (código mais curto) cujo nome bate, para não somar duas
# vezes a mesma receita.
DESTAQUES = [
    ("IPTU", re.compile(r"propriedade predial|\bIPTU\b", re.I)),
    ("ISS", re.compile(r"servi[çc]os de qualquer natureza|\bISS(QN)?\b", re.I)),
    ("ITBI", re.compile(r"transmiss[ãa]o .*inter ?vivos|\bITBI\b", re.I)),
    ("FPM", re.compile(r"fundo de participa[çc][ãa]o dos munic[íi]pios|\bFPM\b", re.I)),
    ("ICMS (cota do município)", re.compile(r"cota-?parte do ICMS|\bICMS\b", re.I)),
    ("IPVA (cota do município)", re.compile(r"cota-?parte do IPVA|\bIPVA\b", re.I)),
    ("Fundeb", re.compile(r"\bFUNDEB\b", re.I)),
    ("SUS", re.compile(r"sistema [úu]nico de sa[úu]de|\bSUS\b", re.I)),
]

_FUNCAO = re.compile(r"(?<![\d.])(\d{2})(?:\.(\d{3}))?\s*[-–]\s*(.+)$")
_CONTA_RECEITA = re.compile(r"(\d(?:\.\d+)+)\s*[-–]?\s*(.*)$")

COLUNAS_RECEITAS = ["codigo", "nivel", "conta", "bruta", "deducoes", "liquida"]
COLUNAS_DESTAQUES = ["destaque", "codigo", "conta", "liquida"]
COLUNAS_AREAS = ["funcao", "subfuncao", "area", "empenhado", "liquidado", "pago"]
COLUNAS_SEM_DADOS = ["secao", "esfera", "responsavel", "motivo", "obrigacao", "fonte_consultada", "consultado_em"]


@dataclass
class Ente:
    ibge: int
    nome: str
    uf: str
    populacao: Optional[int] = None


# --- Siconfi -----------------------------------------------------------------------


def _paginar(client, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    offset = 0
    while True:
        dados = client.get_json(url, {**params, "offset": offset} if offset else params)
        lote = dados.get("items", []) if isinstance(dados, dict) else []
        itens.extend(lote)
        if not (isinstance(dados, dict) and dados.get("hasMore")) or not lote:
            return itens
        offset += len(lote)


def entes_municipais(client, ufs: Iterable[str]) -> List[Ente]:
    ufs = {u.upper() for u in ufs}
    saida = []
    for e in _paginar(client, f"{SICONFI}/entes", {}):
        if str(e.get("esfera", "")).upper() != "M":
            continue
        uf = str(e.get("uf", "")).upper()
        ibge = n.inteiro(e.get("cod_ibge"))
        if ibge and uf in ufs:
            saida.append(Ente(ibge, str(e.get("ente", "")).strip(), uf, n.inteiro(e.get("populacao"))))
    return sorted(saida, key=lambda e: (e.uf, e.ibge))


def _dec(valor: Any) -> Decimal:
    d = n.decimal(valor)
    return d if d is not None else Decimal(0)


def _nivel(codigo: str) -> int:
    """'1.1.1.2.50.0.0' -> 5 (posição do último segmento diferente de zero)."""
    partes = codigo.split(".")
    ultimo = 0
    for i, p in enumerate(partes, 1):
        if p.strip("0"):
            ultimo = i
    return ultimo


def receitas(itens: List[Dict[str, Any]], nivel_max: int = 6) -> List[Dict[str, Any]]:
    """Receita bruta, deduções (Fundeb, transferências…) e líquida por conta."""
    contas: Dict[str, Dict[str, Any]] = {}
    for item in itens:
        texto = str(item.get("conta") or "")
        achado = _CONTA_RECEITA.search(str(item.get("cod_conta") or "")) or _CONTA_RECEITA.search(texto)
        if not achado:
            continue
        codigo = achado.group(1)
        nivel = _nivel(codigo)
        if not 1 <= nivel <= nivel_max:
            continue
        nome = _CONTA_RECEITA.sub(lambda m: m.group(2), texto, count=1).strip() or texto
        c = contas.setdefault(codigo, {"codigo": codigo, "nivel": nivel, "conta": nome,
                                        "bruta": Decimal(0), "deducoes": Decimal(0)})
        valor = _dec(item.get("valor"))
        if str(item.get("coluna", "")).strip().lower() == COLUNA_BRUTA:
            c["bruta"] += valor
        else:
            c["deducoes"] += abs(valor)
    linhas = []
    for c in sorted(contas.values(), key=lambda c: [int(p) for p in c["codigo"].split(".")]):
        c["liquida"] = c["bruta"] - c["deducoes"]
        if c["bruta"] or c["deducoes"]:
            linhas.append(c)
    return linhas


def destaques(linhas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    saida = []
    for nome, padrao in DESTAQUES:
        candidatas = [l for l in linhas if padrao.search(l["conta"])]
        if candidatas:
            l = min(candidatas, key=lambda l: (l["nivel"], l["codigo"]))
            saida.append({"destaque": nome, "codigo": l["codigo"], "conta": l["conta"], "liquida": l["liquida"]})
    return saida


def areas(itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Despesa por função e subfunção. As despesas intraorçamentárias (de um
    órgão do município para outro) aparecem à parte no Siconfi e são somadas."""
    soma: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
    for item in itens:
        fase = FASES.get(str(item.get("coluna", "")).strip().lower())
        if not fase:
            continue
        achado = _FUNCAO.search(str(item.get("conta") or ""))
        if not achado:
            continue
        funcao, subfuncao, nome = achado.group(1), achado.group(2), achado.group(3).strip()
        linha = soma.setdefault(
            (funcao, subfuncao),
            {"funcao": funcao, "subfuncao": subfuncao, "area": nome,
             "empenhado": Decimal(0), "liquidado": Decimal(0), "pago": Decimal(0)},
        )
        linha[fase] += _dec(item.get("valor"))
    return [soma[k] for k in sorted(soma, key=lambda k: (k[0], k[1] or ""))]


# --- IPCA --------------------------------------------------------------------------


def fatores_ipca(client, anos: Iterable[int], hoje: date) -> Tuple[Dict[int, Decimal], Optional[str]]:
    """Fator para levar reais de dezembro de cada ano até o último IPCA publicado."""
    anos = sorted(anos)
    if not anos:
        return {}, None
    dados = []
    inicio = anos[0] + 1
    while inicio <= hoje.year:
        fim = min(inicio + 9, hoje.year)
        dados += client.get_json(IPCA_URL, {"formato": "json", "dataInicial": f"01/01/{inicio}", "dataFinal": f"31/12/{fim}"})
        inicio = fim + 1
    meses = sorted(
        (d, v) for d, v in ((n.data(i.get("data")), n.decimal(i.get("valor"))) for i in dados) if d and v is not None
    )
    fatores = {}
    for ano in anos:
        f = Decimal(1)
        for d, v in meses:
            if d.year > ano:
                f *= 1 + v / 100
        fatores[ano] = f.quantize(Decimal("0.000001"))
    ultimo = meses[-1][0].strftime("%Y-%m") if meses else None
    return fatores, ultimo


# --- arquivo do ano ----------------------------------------------------------------


def prazo_dca(ano: int) -> date:
    """LRF, art. 51: contas do ano entregues à União até 30 de abril do ano seguinte."""
    return date(ano + 1, 4, 30)


def documento_ano(
    ente: Ente,
    ano: int,
    itens_receitas: List[Dict[str, Any]],
    itens_funcoes: List[Dict[str, Any]],
    hoje: date,
    fator: Optional[Decimal],
    ipca_ate: Optional[str],
) -> str:
    rec = receitas(itens_receitas)
    are = areas(itens_funcoes)
    # Itens vieram mas nada foi reconhecido: o formato do Siconfi mudou.
    for nome, itens, lista in (("I-C", itens_receitas, rec), ("I-E", itens_funcoes, are)):
        if itens and not lista:
            logger.warning("Siconfi %s %s %s: %s itens sem conta reconhecida, ex.: %s",
                           ente.ibge, ano, nome, len(itens), itens[:3])
    sem_dados = []
    for secao, lista, anexo in (("receitas", rec, ANEXO_RECEITAS), ("areas", are, ANEXO_FUNCOES)):
        if lista:
            continue
        atrasado = hoje > prazo_dca(ano)
        sem_dados.append({
            "secao": secao,
            "esfera": "municipal",
            "responsavel": f"Prefeitura de {ente.nome} ({ente.uf})",
            "motivo": (
                f"A Declaração de Contas Anuais de {ano} ({anexo}) não está no Siconfi"
                if atrasado
                else f"A Declaração de Contas Anuais de {ano} ainda está no prazo de entrega ({prazo_dca(ano):%d/%m/%Y})"
            ),
            "obrigacao": "Lei de Responsabilidade Fiscal (LC 101/2000), art. 51" if atrasado else None,
            "fonte_consultada": SICONFI_SITE,
            "consultado_em": hoje,
        })
    meta = {
        "tipo": "municipio-ano",
        "ibge": ente.ibge,
        "municipio": ente.nome,
        "uf": ente.uf,
        "ano": ano,
        "populacao": ente.populacao,
        "ipca_fator": fator,
        "ipca_ate": ipca_ate,
        "atualizado": hoje,
        "fonte": f"{SICONFI_SITE} (DCA, anexos I-C e I-E)",
    }
    tabelas: Dict[str, List[Dict[str, Any]]] = {}
    textos = {}
    if rec:
        tabelas["destaques"] = destaques(rec)
        tabelas["receitas"] = rec
        textos["destaques"] = (
            "## Arrecadação\n\nValores em reais do ano. Para levar a valores de hoje, "
            "multiplique pelo `ipca_fator` do cabeçalho. Receita líquida = bruta menos "
            "deduções (como a parte que vai para o Fundeb)."
        )
    if are:
        tabelas["areas"] = are
        textos["areas"] = (
            "## Gastos por área\n\nFunção (saúde, educação…) e subfunção. Empenhado é o "
            "que foi reservado, liquidado é o serviço entregue e pago é o que saiu do caixa."
        )
    if sem_dados:
        tabelas["sem-dados"] = sem_dados
        textos["sem-dados"] = "## Sem dados"
    return md.escrever(
        {k: v for k, v in meta.items() if v is not None},
        tabelas,
        colunas={"destaques": COLUNAS_DESTAQUES, "receitas": COLUNAS_RECEITAS,
                 "areas": COLUNAS_AREAS, "sem-dados": COLUNAS_SEM_DADOS},
        titulo=f"{ente.nome} ({ente.uf}), {ano}",
        textos=textos,
    )


# --- coleta ------------------------------------------------------------------------


def _publicado(client, ente: Ente, ano: int) -> Optional[str]:
    """Arquivo do mesmo ano já publicado no GitHub Pages, se houver."""
    try:
        texto = client.get_bytes(f"{PUBLICADO}/v1/municipios/{ente.uf.lower()}/{ente.ibge}/{ano}.md").decode("utf-8")
        doc = md.ler(texto)
    except Exception:
        return None
    # Arquivo publicado sem dados não serve: o município pode ter entregue depois.
    return None if "sem-dados" in doc.tabelas else texto


def gerar(
    novo_cliente: Callable[[], Any],
    saida: Path,
    anos: Iterable[int],
    ufs: Iterable[str],
    hoje: Optional[date] = None,
    limite_siconfi: Optional[int] = None,
    trabalhadores: int = 4,
    reaproveitar: bool = True,
) -> Dict[str, int]:
    """Grava os arquivos de cada município e ano.

    `limite_siconfi` limita quantos pares (município, ano) são buscados no
    Siconfi nesta execução; o resto fica para a próxima, sem apagar o que já
    foi publicado. Os dois últimos anos sempre são buscados de novo, porque as
    prefeituras ainda podem corrigir (retificar) a declaração.
    """
    hoje = hoje or date.today()
    anos = sorted(set(anos))
    principal = novo_cliente()
    try:
        entes = entes_municipais(principal, ufs)
    except Exception as erro:
        # Sem a lista do Siconfi, usa a do IBGE guardada no repositório.
        logger.warning("Lista de entes do Siconfi indisponível (%s); usando a lista do IBGE", erro)
        from .eleitos import municipios_ibge

        filtro = {u.upper() for u in ufs}
        entes = sorted(
            (Ente(cod, nome, uf) for (uf, _), (cod, nome) in municipios_ibge().items() if uf in filtro),
            key=lambda e: (e.uf, e.ibge),
        )
    fatores, ipca_ate = fatores_ipca(principal, anos, hoje)
    recentes = {hoje.year - 1, hoje.year}
    pares = [(e, a) for a in sorted(anos, reverse=True) for e in entes]

    contagem = {"siconfi": 0, "reaproveitados": 0, "pendentes": 0}
    trava = threading.Lock()
    orcamento = [limite_siconfi if limite_siconfi is not None else len(pares)]
    local = threading.local()

    def cliente():
        if not hasattr(local, "c"):
            local.c = novo_cliente()
        return local.c

    def processar(par: Tuple[Ente, int]) -> None:
        ente, ano = par
        c = cliente()
        texto = None
        if reaproveitar and ano not in recentes:
            texto = _publicado(c, ente, ano)
            if texto:
                tipo = "reaproveitados"
        if texto is None:
            with trava:
                pode = orcamento[0] > 0
                if pode:
                    orcamento[0] -= 1
            if not pode:
                texto = _publicado(c, ente, ano) if reaproveitar else None
                tipo = "reaproveitados" if texto else "pendentes"
            else:
                try:
                    base = {"an_exercicio": ano, "id_ente": ente.ibge}
                    rec = _paginar(c, f"{SICONFI}/dca", {**base, "no_anexo": ANEXO_RECEITAS})
                    fun = _paginar(c, f"{SICONFI}/dca", {**base, "no_anexo": ANEXO_FUNCOES})
                except Exception as erro:  # um município fora do ar não para a coleta
                    logger.warning("Siconfi %s %s: %s", ente.ibge, ano, erro)
                    texto = _publicado(c, ente, ano) if reaproveitar else None
                    tipo = "reaproveitados" if texto else "pendentes"
                else:
                    texto = documento_ano(ente, ano, rec, fun, hoje, fatores.get(ano), ipca_ate)
                    tipo = "siconfi"
        with trava:
            contagem[tipo] += 1
        if texto:
            caminho = saida / "v1" / "municipios" / ente.uf.lower() / str(ente.ibge) / f"{ano}.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(texto, encoding="utf-8")

    if trabalhadores <= 1:
        for par in pares:
            processar(par)
    else:
        with ThreadPoolExecutor(trabalhadores) as pool:
            list(pool.map(processar, pares))
    logger.info(
        "Finanças municipais: %s municípios, anos %s: %s do Siconfi, %s reaproveitados, %s para a próxima coleta",
        len(entes), anos, contagem["siconfi"], contagem["reaproveitados"], contagem["pendentes"],
    )
    return contagem
