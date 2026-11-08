"""Atuação parlamentar dos deputados federais.

O que a página de cada deputado na Câmara mostra além de votos e gastos, a
partir dos dados abertos (dadosabertos.camara.leg.br), sem raspar o site:

- propostas de autoria (projetos de lei, PECs, PLPs, PDLs e resoluções),
  com a situação atual de cada uma, e quantas emendas e requerimentos
  apresentou: arquivos anuais proposicoes-{ano} e proposicoesAutores-{ano};
- relatorias: pareceres de relator que ele assinou, agrupados pela proposta
  relatada (o parecer é uma proposição de autoria do próprio relator);
- presença no Plenário: dias com sessão deliberativa em que registrou
  presença, contados só no período em que estava em exercício (histórico do
  mandato na API); a Câmara não publica nos dados abertos as ausências
  justificadas, por isso o app mostra só a presença registrada;
- discursos: total do ano por tipo e os mais recentes, com link para o texto;
- comissões e frentes parlamentares de que faz parte.

Tudo vai para a tabela Atividade, no formato que a API do AraraGov publica.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import delete, insert, select

from ..db import Atividade, Politico, sessao
from ..http import HttpClient
from ._comum import ler_csv
from .camara import API, ARQUIVOS, legislatura_atual

logger = logging.getLogger(__name__)

CASA = "camara"
PAGINA_PROPOSTA = "https://www.camara.leg.br/propostas-legislativas/{id}"
TRABALHOS = 4

# Propostas legislativas de autoria, como a página do deputado conta.
PROPOSTAS = {"PL", "PLP", "PEC", "PDL", "PRC"}
# Pareceres assinados pelo relator.
PARECERES = {"PRL", "PRLP", "PRLE", "PPP", "PEP", "PES", "PSS", "PPR", "PRV", "RRL", "CVO"}
# A relatoria só conta quando a proposta relatada é legislativa; pareceres a
# requerimentos de informação (feitos pela Mesa) ficam de fora.
RELATADAS = PROPOSTAS | {"MPV", "PLV", "PLN", "MSC", "TVR", "INA"}
EMENDAS = {"EMC", "EMP", "EMR", "ESB", "SBT", "SBR", "SSP", "ERD", "EMA"}
REQUERIMENTOS = {"REQ", "RIC", "INC", "RCP", "PFC", "SIT", "RPD", "RPDR", "REC", "DTQ"}

EMENTA_MAX = 240
DISCURSOS_RECENTES = 8
# Propostas relatadas apresentadas antes dos anos baixados: busca na API até
# este limite por ano coletado. Relatoria sem a proposta identificada fica de
# fora (não dá para saber se é legislativa).
ORCAMENTO_API = 800

# id -> (rótulo, sigla do tipo, ementa, situação), acumulado ao longo dos anos
# coletados na mesma execução (os anos vão do mais antigo ao mais recente).
_indice: Dict[int, Tuple[str, str, str, Optional[str]]] = {}
# código do deputado -> períodos em exercício [(início, fim)]
_exercicio: Dict[int, List[Tuple[date, date]]] = {}


def _int(texto: Any) -> Optional[int]:
    try:
        return int(str(texto).strip().rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        return None


def _ementa(texto: Optional[str]) -> str:
    t = " ".join((texto or "").split())
    return t if len(t) <= EMENTA_MAX else t[: EMENTA_MAX - 1].rstrip() + "…"


def _rotulo(sigla: str, numero: Any, ano: Any) -> str:
    return f"{sigla} {numero}/{ano}"


def conclusao_parecer(ementa: Optional[str]) -> Optional[str]:
    """ "Parecer do Relator, Dep. Fulano (PL-BA), pela aprovação." -> "pela aprovação"."""
    m = re.search(r"\)\s*,\s*(pel[ao]s?\s.+?)\.?\s*$", ementa or "", re.S)
    if not m:
        return None
    texto = " ".join(m.group(1).split())
    return texto if len(texto) <= 200 else texto[:199].rstrip() + "…"


def _deputados() -> Set[int]:
    with sessao() as s:
        codigos = set(s.execute(select(Politico.codigo).where(Politico.casa == CASA)).scalars())
    if not codigos:
        raise RuntimeError("Nenhum deputado no banco. Rode antes: araragov coletar camara-deputados")
    return codigos


def _gravar(linhas: List[Dict[str, Any]], tipos: Iterable[str], ano: Optional[int]) -> None:
    with sessao() as s:
        filtro = [Atividade.casa == CASA, Atividade.tipo.in_(list(tipos))]
        filtro.append(Atividade.ano == ano if ano is not None else Atividade.ano.is_(None))
        s.execute(delete(Atividade).where(*filtro))
        if linhas:
            s.execute(insert(Atividade), linhas)


# ---------------------------------------------------------------- proposições


def _buscar_relatadas(client: HttpClient, ids: List[int]) -> None:
    """Completa o índice com propostas de anos que não foram baixados."""
    ids = ids[:ORCAMENTO_API]

    def uma(pid: int):
        try:
            d = client.get_json(f"{API}/proposicoes/{pid}").get("dados") or {}
        except Exception as e:  # uma proposta fora do ar não derruba as outras
            logger.debug("Câmara: proposição %s indisponível: %s", pid, e)
            return
        sigla = d.get("siglaTipo") or ""
        situacao = (d.get("statusProposicao") or {}).get("descricaoSituacao")
        _indice[pid] = (_rotulo(sigla, d.get("numero"), d.get("ano")), sigla, _ementa(d.get("ementa")), situacao)

    with ThreadPoolExecutor(TRABALHOS) as ex:
        list(ex.map(uma, ids))


def ler_producao(proposicoes: Iterable[Dict[str, str]], autores: Iterable[Dict[str, str]],
                 deputados: Set[int]) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, List[Dict[str, Any]]]]:
    """Propostas, emendas e requerimentos de cada deputado no ano, e os
    pareceres de relator (ainda sem a proposta relatada resolvida)."""
    props: Dict[int, Dict[str, str]] = {}
    for p in proposicoes:
        pid = _int(p.get("id"))
        if pid is None:
            continue
        sigla = (p.get("siglaTipo") or "").strip()
        if sigla in PROPOSTAS or sigla in PARECERES or sigla in RELATADAS or sigla in EMENDAS or sigla in REQUERIMENTOS:
            props[pid] = p
        if sigla in RELATADAS:
            _indice[pid] = (_rotulo(sigla, p.get("numero"), p.get("ano")), sigla, _ementa(p.get("ementa")),
                            p.get("ultimoStatus_descricaoSituacao") or None)
        else:  # só o tipo, para saber que não é proposta legislativa
            _indice[pid] = (None, sigla, None, None)

    producao: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {"propostas": [], "emendas": 0, "requerimentos": 0, "pedidos_informacao": 0}
    )
    pareceres: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    vistos: Set[Tuple[int, int]] = set()
    for a in autores:
        dep, pid = _int(a.get("idDeputadoAutor")), _int(a.get("idProposicao"))
        if dep not in deputados or pid not in props or (a.get("proponente") or "").strip() != "1":
            continue
        if (dep, pid) in vistos:
            continue
        vistos.add((dep, pid))
        p = props[pid]
        sigla = p["siglaTipo"].strip()
        primeiro = (a.get("ordemAssinatura") or "").strip() == "1"
        if sigla in PROPOSTAS:
            producao[dep]["propostas"].append([
                pid, _rotulo(sigla, p.get("numero"), p.get("ano")), _ementa(p.get("ementa")),
                (p.get("dataApresentacao") or "")[:10] or None,
                p.get("ultimoStatus_descricaoSituacao") or None, 1 if primeiro else 0,
            ])
        elif sigla in PARECERES:
            pareceres[dep].append({
                "principal": _int(p.get("uriPropPrincipal")),
                "data": (p.get("dataApresentacao") or "")[:10] or None,
                "conclusao": conclusao_parecer(p.get("ementa")),
            })
        elif sigla in EMENDAS:
            producao[dep]["emendas"] += 1
        elif sigla in REQUERIMENTOS:
            producao[dep]["requerimentos"] += 1
            if sigla == "RIC":
                producao[dep]["pedidos_informacao"] += 1
    return producao, pareceres


def relatorias(pareceres: List[Dict[str, Any]]) -> List[List[Any]]:
    """Um item por proposta relatada (o parecer mais recente), só as legislativas."""
    por_proposta: Dict[int, Dict[str, Any]] = {}
    for p in pareceres:
        pid = p["principal"]
        if pid is None:
            continue
        atual = por_proposta.get(pid)
        if atual is None or (p["data"] or "") > (atual["data"] or ""):
            por_proposta[pid] = p
    saida = []
    for pid, p in por_proposta.items():
        info = _indice.get(pid)
        if info is None or info[1] not in RELATADAS:
            continue
        rotulo, _, ementa, situacao = info
        saida.append([pid, rotulo, ementa, p["data"], p["conclusao"], situacao])
    return sorted(saida, key=lambda r: r[3] or "", reverse=True)


def coletar_proposicoes(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    deputados = _deputados()
    proposicoes = ler_csv(client.get_bytes(f"{ARQUIVOS}/proposicoes/csv/proposicoes-{ano}.csv"))
    autores = ler_csv(client.get_bytes(f"{ARQUIVOS}/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"))
    producao, pareceres = ler_producao(proposicoes, autores, deputados)

    faltam = sorted({p["principal"] for lista in pareceres.values() for p in lista
                     if p["principal"] is not None and p["principal"] not in _indice})
    if faltam:
        _buscar_relatadas(client, faltam)

    linhas = []
    codigos = sorted(set(producao) | set(pareceres))
    if limite:
        codigos = codigos[:limite]
    for cod in codigos:
        dados = dict(producao[cod]) if cod in producao else {"propostas": [], "emendas": 0, "requerimentos": 0, "pedidos_informacao": 0}
        dados["propostas"] = sorted(dados["propostas"], key=lambda r: r[3] or "", reverse=True)
        dados["relatorias"] = relatorias(pareceres.get(cod, []))
        linhas.append({"casa": CASA, "codigo_politico": cod, "ano": ano, "tipo": "producao", "dados": dados})
    _gravar(linhas, ["producao"], ano)
    logger.info("Câmara %s: produção legislativa de %s deputados (%s propostas relatadas buscadas na API)",
                ano, len(linhas), min(len(faltam), ORCAMENTO_API))
    return len(linhas)


# ------------------------------------------------------------ mandato e presença


def periodos_exercicio(historico: List[Dict[str, Any]], hoje: Optional[date] = None) -> List[Tuple[date, date]]:
    """Períodos em exercício a partir do histórico do deputado na API."""
    hoje = hoje or date.today()
    eventos = sorted(
        ((h.get("dataHora") or "")[:10], h.get("situacao")) for h in historico if h.get("situacao") and h.get("dataHora")
    )
    periodos, inicio = [], None
    for dia, situacao in eventos:
        d = date.fromisoformat(dia)
        if situacao == "Exercício":
            inicio = inicio or d
        elif inicio is not None:
            periodos.append((inicio, d))
            inicio = None
    if inicio is not None:
        periodos.append((inicio, hoje))
    return periodos


def _carregar_exercicio(client: HttpClient, codigos: Iterable[int]) -> None:
    faltam = [c for c in codigos if c not in _exercicio]

    def um(cod: int):
        try:
            return cod, periodos_exercicio(client.get_json(f"{API}/deputados/{cod}/historico").get("dados") or [])
        except Exception as e:
            logger.debug("Câmara: histórico do deputado %s indisponível: %s", cod, e)
            return cod, None

    with ThreadPoolExecutor(TRABALHOS) as ex:
        for cod, periodos in ex.map(um, faltam):
            if periodos is not None:
                _exercicio[cod] = periodos


def _em_exercicio(cod: int, dia: date) -> bool:
    periodos = _exercicio.get(cod)
    return periodos is None or any(i <= dia <= f for i, f in periodos)


def dias_de_sessao(eventos: Iterable[Dict[str, str]]) -> Dict[str, date]:
    """id do evento -> dia, das sessões deliberativas do Plenário que aconteceram."""
    saida = {}
    for e in eventos:
        if (e.get("descricaoTipo") or "").strip() != "Sessão Deliberativa":
            continue
        if "cancel" in (e.get("situacao") or "").lower():
            continue
        dia = (e.get("dataHoraInicio") or "")[:10]
        if dia:
            saida[e["id"]] = date.fromisoformat(dia)
    return saida


def coletar_presenca(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    deputados = _deputados()
    sessoes = dias_de_sessao(ler_csv(client.get_bytes(f"{ARQUIVOS}/eventos/csv/eventos-{ano}.csv")))
    presentes: Dict[int, Set[date]] = defaultdict(set)
    for linha in ler_csv(client.get_bytes(f"{ARQUIVOS}/eventosPresencaDeputados/csv/eventosPresencaDeputados-{ano}.csv")):
        dia = sessoes.get(linha.get("idEvento"))
        cod = _int(linha.get("idDeputado"))
        if dia is not None and cod in deputados:
            presentes[cod].add(dia)
    codigos = sorted(presentes)
    if limite:
        codigos = codigos[:limite]
    _carregar_exercicio(client, codigos)
    dias = sorted(set(sessoes.values()))
    linhas = []
    for cod in codigos:
        no_mandato = [d for d in dias if _em_exercicio(cod, d)]
        if not no_mandato:
            continue
        linhas.append({"casa": CASA, "codigo_politico": cod, "ano": ano, "tipo": "presenca", "dados": {
            "dias_presente": len(presentes[cod] & set(no_mandato)),
            "dias_sessao": len(no_mandato),
            "periodo_parcial": len(no_mandato) < len(dias),
        }})
    _gravar(linhas, ["presenca"], ano)
    logger.info("Câmara %s: presença no Plenário de %s deputados (%s dias com sessão)", ano, len(linhas), len(dias))
    return len(linhas)


# ------------------------------------------------------------------- discursos


def _trecho(d: Dict[str, Any]) -> str:
    texto = d.get("sumario") or d.get("transcricao") or ""
    texto = re.sub(r"^\s*(O|A)\s+SRA?\.\s.*?\)\s*-\s*", "", texto, count=1, flags=re.S)
    texto = " ".join(texto.split())
    return texto if len(texto) <= 220 else texto[:219].rstrip() + "…"


def resumo_discursos(discursos: List[Dict[str, Any]]) -> Dict[str, Any]:
    ordenados = sorted(discursos, key=lambda d: d.get("dataHoraInicio") or "", reverse=True)
    return {
        "total": len(discursos),
        "por_tipo": dict(Counter((d.get("tipoDiscurso") or "Outro").strip().capitalize() for d in discursos).most_common()),
        "recentes": [
            [(d.get("dataHoraInicio") or "")[:10] or None, (d.get("tipoDiscurso") or "").strip().capitalize() or None,
             _trecho(d), d.get("urlTexto") or d.get("urlVideo") or None]
            for d in ordenados[:DISCURSOS_RECENTES]
        ],
    }


def coletar_discursos(client: HttpClient, ano: int, limite: Optional[int] = None) -> int:
    """Discursos do ano de quem esteve em exercício (presença registrada ou
    mandato na legislatura do ano)."""
    with sessao() as s:
        codigos = sorted(set(s.execute(
            select(Atividade.codigo_politico).where(Atividade.casa == CASA, Atividade.ano == ano, Atividade.tipo == "presenca")
        ).scalars()))
        if not codigos:
            codigos = sorted(set(s.execute(
                select(Politico.codigo).where(Politico.casa == CASA, Politico.em_exercicio.is_(True))
            ).scalars()))
    if limite:
        codigos = codigos[:limite]
    params = {"dataInicio": f"{ano}-01-01", "dataFim": f"{ano}-12-31", "itens": 100,
              "ordenarPor": "dataHoraInicio", "ordem": "DESC"}

    def um(cod: int):
        itens, pagina = [], 1
        try:
            while True:
                d = client.get_json(f"{API}/deputados/{cod}/discursos", {**params, "pagina": pagina})
                itens.extend(d.get("dados") or [])
                if not any(l.get("rel") == "next" for l in d.get("links") or []) or pagina >= 30:
                    return cod, itens
                pagina += 1
        except Exception as e:
            logger.warning("Câmara: discursos do deputado %s (%s) indisponíveis: %s", cod, ano, e)
            return cod, None

    with ThreadPoolExecutor(TRABALHOS) as ex:
        resultados = list(ex.map(um, codigos))
    linhas = [{"casa": CASA, "codigo_politico": cod, "ano": ano, "tipo": "discursos", "dados": resumo_discursos(itens)}
              for cod, itens in resultados if itens]
    if codigos and all(itens is None for _, itens in resultados):
        raise RuntimeError(f"Nenhum discurso respondeu ({ano})")
    _gravar(linhas, ["discursos"], ano)
    logger.info("Câmara %s: discursos de %s deputados", ano, len(linhas))
    return len(linhas)


def coletar_atividade(client: HttpClient, ano: int, ano_final: int, limite: Optional[int] = None) -> int:
    """Produção legislativa e presença de todo ano coletado; discursos só do
    ano atual e do anterior (um pedido por deputado)."""
    partes = [coletar_proposicoes, coletar_presenca] + ([coletar_discursos] if ano >= ano_final - 1 else [])
    total, falhas = 0, []
    for parte in partes:  # uma parte fora do ar não impede as outras
        try:
            total += parte(client, ano, limite)
        except Exception as e:
            logger.warning("Câmara %s: %s falhou: %s", ano, parte.__name__, e)
            falhas.append(parte.__name__)
    if falhas:
        raise RuntimeError(f"Atividade da Câmara {ano}: falharam {', '.join(falhas)}")
    return total


# -------------------------------------------------------- comissões e frentes


def ler_comissoes(linhas: Iterable[Dict[str, str]], deputados: Set[int]) -> Dict[int, List[List[Any]]]:
    saida: Dict[int, List[List[Any]]] = defaultdict(list)
    for l in linhas:
        cod = _int(l.get("uriDeputado"))
        if cod not in deputados:
            continue
        saida[cod].append([
            (l.get("siglaOrgao") or "").strip() or None,
            (l.get("nomePublicacaoOrgao") or l.get("nomeOrgao") or "").strip(),
            (l.get("cargo") or "").strip() or None,
            (l.get("dataInicio") or "")[:10] or None,
            (l.get("dataFim") or "")[:10] or None,
        ])
    return saida


def _ordenar_comissoes(itens: List[List[Any]]) -> List[List[Any]]:
    """Junta os períodos seguidos no mesmo órgão e cargo (a Câmara registra cada
    renovação como uma linha) e põe as atuais primeiro, depois as que
    terminaram mais recentemente. Bancadas de partido ficam de fora: o partido
    já aparece no perfil e a lista da Câmara não acompanha trocas de partido."""
    juntos: Dict[Tuple[Any, Any], List[Any]] = {}
    for sigla, nome, cargo, inicio, fim in itens:
        if nome.lower().startswith("bancada d") or sigla in ("CN", "PLENARIO"):
            continue
        atual = juntos.get((sigla, cargo))
        if atual is None:
            juntos[(sigla, cargo)] = [sigla, nome, cargo, inicio, fim]
            continue
        atual[3] = min(filter(None, [atual[3], inicio]), default=None)
        atual[4] = None if atual[4] is None or fim is None else max(atual[4], fim)
    return sorted(juntos.values(), key=lambda r: (r[4] is not None, -int((r[4] or r[3] or "0").replace("-", "") or 0), r[1]))


def ler_frentes(linhas: Iterable[Dict[str, str]], deputados: Set[int], legislatura: int) -> Dict[int, List[List[Any]]]:
    saida: Dict[int, List[List[Any]]] = defaultdict(list)
    for l in linhas:
        if _int(l.get("deputado_.idLegislatura")) != legislatura:
            continue
        cod = _int(l.get("deputado_.id"))
        if cod not in deputados:
            continue
        papel = (l.get("deputado_.titulo") or "").strip()
        coordena = papel.lower().startswith("coord")
        saida[cod].append([_int(l.get("id")), " ".join((l.get("titulo") or "").split()), 1 if coordena else 0])
    for itens in saida.values():
        itens.sort(key=lambda r: (-r[2], r[1]))
    return saida


def coletar_comissoes(client: HttpClient, limite: Optional[int] = None) -> int:
    deputados = _deputados()
    atual = legislatura_atual(client)
    comissoes: Dict[int, List[List[Any]]] = defaultdict(list)
    for leg in (atual - 1, atual):
        try:
            arquivo = client.get_bytes(f"{ARQUIVOS}/orgaosDeputados/csv/orgaosDeputados-L{leg}.csv")
        except Exception as e:
            logger.warning("Câmara: comissões da legislatura %s indisponíveis: %s", leg, e)
            continue
        for cod, itens in ler_comissoes(ler_csv(arquivo), deputados).items():
            comissoes[cod] = itens + comissoes[cod]
    frentes = ler_frentes(ler_csv(client.get_bytes(f"{ARQUIVOS}/frentesDeputados/csv/frentesDeputados.csv")), deputados, atual)
    codigos = sorted(set(comissoes) | set(frentes))
    if limite:
        codigos = codigos[:limite]
    linhas = []
    for cod in codigos:
        if comissoes.get(cod):
            itens = _ordenar_comissoes(comissoes[cod])
            linhas.append({"casa": CASA, "codigo_politico": cod, "ano": None, "tipo": "comissoes", "dados": {"itens": itens}})
        if frentes.get(cod):
            linhas.append({"casa": CASA, "codigo_politico": cod, "ano": None, "tipo": "frentes",
                           "dados": {"legislatura": atual, "itens": frentes[cod]}})
    _gravar(linhas, ["comissoes", "frentes"], None)
    logger.info("Câmara: comissões e frentes de %s deputados", len(codigos))
    return len(codigos)
