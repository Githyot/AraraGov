"""Processos e ocorrências: registros oficiais ligados a cada político.

O AraraGov só informa; não acusa. Por isso esta coleta lê apenas cadastros
oficiais e guarda, para cada registro, a situação, a data e o link da fonte:

- TSE (candidaturas de 2018 e 2022): candidatura indeferida, cassada ou com
  recurso, o motivo da cassação quando houver, e o link da página da
  candidatura, onde ficam as certidões criminais que todo candidato entrega.
- CGU, CEIS e CNEP: sanções a pessoas físicas (ex.: proibição de contratar
  com o poder público por improbidade, registrada pelo CNJ).
- TCU: inabilitados para cargo em comissão ou função de confiança.

Homônimos: CGU e TCU publicam o CPF com dígitos ocultos. Um registro só é
ligado ao político quando o nome é igual E os dígitos visíveis batem com o CPF
da candidatura dele no TSE. O CPF é lido só em memória para essa conferência;
nunca é gravado no banco nem publicado. Sem CPF conferível, o registro não
entra (melhor faltar do que atribuir a alguém o processo de um homônimo).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from sqlalchemy import delete, select

from ..db import ConsultaOcorrencia, Ocorrencia, Politico, VerificacaoOcorrencia, sessao
from ..http import HttpClient
from .gabinete import _chave_nome
from .tse import CANDIDATOS_URL

logger = logging.getLogger(__name__)

ANOS_TSE = (2018, 2022)
MOTIVO_CASSACAO_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/motivo_cassacao/motivo_cassacao_{ano}.zip"
DIVULGACAND = "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/{ano}/{eleicao}/{ue}/{sq}"
SANCOES_URL = "https://portaldatransparencia.gov.br/download-de-dados/{cadastro}/{data}"
SANCOES_PAGINA = "https://portaldatransparencia.gov.br/sancoes/{cadastro}"
TCU_URL = "https://contas.tcu.gov.br/ords/condenacao/consulta/inabilitados"
TCU_PAGINA = "https://contas.tcu.gov.br/ords/f?p=1660:1"

CONFERIDO_TSE = "Candidatura do próprio político no TSE (nome, cargo e estado)"
CONFERIDO_CPF = "Nome igual e dígitos do CPF conferidos com a candidatura no TSE"

# Cargo no TSE que corresponde a cada tipo de casa do AraraGov.
CARGOS_TSE = {
    "camara": {"DEPUTADO FEDERAL"},
    "senado": {"SENADOR", "1º SUPLENTE", "2º SUPLENTE", "1O SUPLENTE", "2O SUPLENTE"},
    "al": {"DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"},
    "gov": {"GOVERNADOR", "VICE-GOVERNADOR"},
}

# DS_DETALHE_SITUACAO_CAND -> (situação no app, título). Renúncia, falecimento
# e cancelamento pelo partido não entram: não dizem nada sobre conduta.
DETALHES_TSE = {
    "INDEFERIDO": ("decidido", "Candidatura indeferida pela Justiça Eleitoral"),
    "INDEFERIDO COM RECURSO": ("recurso", "Candidatura indeferida, com recurso"),
    "CASSADO": ("decidido", "Registro ou diploma cassado pela Justiça Eleitoral"),
    "CASSADO COM RECURSO": ("recurso", "Registro ou diploma cassado, com recurso"),
    "DEFERIDO COM RECURSO": ("em_andamento", "Candidatura aprovada, com recurso contra o registro"),
    "NÃO CONHECIMENTO DO PEDIDO": ("decidido", "Pedido de registro não conhecido pela Justiça Eleitoral"),
}

SITUACOES = {
    "em_andamento", "recurso", "condenado", "condenado_definitivo", "absolvido", "arquivado", "extinto",
    "sancao_vigente", "sancao_encerrada", "decidido", "informativo",
}


def so_digitos(texto: Optional[str]) -> str:
    return re.sub(r"\D", "", texto or "")


def cpf_valido(texto: Optional[str]) -> Optional[str]:
    d = so_digitos(texto)
    return d if len(d) == 11 and len(set(d)) > 1 else None


def cpf_confere(mascarado: Optional[str], cpf: Optional[str], minimo: int = 6) -> bool:
    """Compara um CPF publicado com dígitos ocultos ("***.456.789-**") com o
    CPF completo, nas posições visíveis. Exige ao menos `minimo` dígitos."""
    if not cpf or not mascarado:
        return False
    limpo = re.sub(r"[.\-/\s]", "", mascarado.strip())
    if len(limpo) != 11:
        return False
    visiveis = [(i, c) for i, c in enumerate(limpo) if c.isdigit()]
    return len(visiveis) >= minimo and all(cpf[i] == c for i, c in visiveis)


def _data_br(texto: Optional[str]) -> Optional[date]:
    t = (texto or "").strip()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _csvs(conteudo: bytes, filtro=lambda nome: True) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in sorted(z.namelist()):
            if nome.lower().endswith(".csv") and filtro(nome):
                texto = z.read(nome).decode("latin-1")
                yield from csv.DictReader(io.StringIO(texto), delimiter=";")


# --- TSE -----------------------------------------------------------------------------------


@dataclass
class Candidatura:
    ano: int
    sq: str
    eleicao: str
    ue: str
    uf: str
    cargo: str
    nome: str  # chave do nome civil
    urna: str  # chave do nome de urna
    detalhe: str
    cpf: Optional[str] = None
    motivos: List[str] = field(default_factory=list)

    @property
    def link(self) -> str:
        return DIVULGACAND.format(ano=self.ano, eleicao=self.eleicao, ue=self.ue, sq=self.sq)


def ler_candidaturas(conteudo: bytes, ano: int) -> List[Candidatura]:
    """Candidaturas a cargos estaduais e federais (pula os arquivos BR/BRASIL,
    que repetem as linhas por estado)."""
    cargos = set().union(*CARGOS_TSE.values())
    lista = []
    vistos: Set[str] = set()
    for l in _csvs(conteudo, lambda n: not re.search(r"_(BR|BRASIL)\.csv$", n, re.I)):
        cargo = (l.get("DS_CARGO") or "").strip().upper()
        sq = (l.get("SQ_CANDIDATO") or "").strip()
        if cargo not in cargos or not sq or sq in vistos:
            continue
        vistos.add(sq)
        lista.append(Candidatura(
            ano=ano, sq=sq,
            eleicao=(l.get("CD_ELEICAO") or "").strip(),
            ue=(l.get("SG_UE") or l.get("SG_UF") or "").strip(),
            uf=(l.get("SG_UF") or "").strip().upper(),
            cargo=cargo,
            nome=_chave_nome(l.get("NM_CANDIDATO") or ""),
            urna=_chave_nome(l.get("NM_URNA_CANDIDATO") or ""),
            detalhe=(l.get("DS_DETALHE_SITUACAO_CAND") or "").strip().upper(),
            cpf=cpf_valido(l.get("NR_CPF_CANDIDATO")),
        ))
    return lista


def ler_motivos(conteudo: bytes) -> Dict[str, List[str]]:
    motivos: Dict[str, List[str]] = defaultdict(list)
    for l in _csvs(conteudo):
        sq = (l.get("SQ_CANDIDATO") or "").strip()
        m = (l.get("DS_MOTIVO_CASSACAO") or "").strip()
        if sq and m and m.upper() not in ("#NULO", "#NULO#", "#NE") and m not in motivos[sq]:
            motivos[sq].append(m[:1].upper() + m[1:].lower())
    return motivos


def _tipo_casa(casa: str) -> str:
    return casa if casa in ("camara", "senado") else casa.split("-", 1)[0]


def casar_candidaturas(politicos: Iterable[Politico], candidaturas: List[Candidatura]) -> Dict[Tuple[str, int], List[Candidatura]]:
    """(casa, código) -> candidaturas da mesma pessoa. Casa pelo nome civil (ou
    de urna), cargo e estado; com CPF, junta também as outras candidaturas da
    pessoa (ex.: deputado que concorreu a governador). Nome que aparece em
    candidaturas de CPFs diferentes é ambíguo e fica de fora."""
    por_nome: Dict[Tuple[str, str, str], List[Candidatura]] = defaultdict(list)
    por_cpf: Dict[str, List[Candidatura]] = defaultdict(list)
    for c in candidaturas:
        tipo = next((t for t, cargos in CARGOS_TSE.items() if c.cargo in cargos), None)
        if tipo is None:
            continue
        por_nome[(tipo, c.uf, c.nome)].append(c)
        if c.urna and c.urna != c.nome:
            por_nome[(tipo, c.uf, "urna:" + c.urna)].append(c)
        if c.cpf:
            por_cpf[c.cpf].append(c)

    saida: Dict[Tuple[str, int], List[Candidatura]] = {}
    ambiguos = 0
    for p in politicos:
        tipo = _tipo_casa(p.casa)
        uf = (p.uf or "").upper()
        achadas = por_nome.get((tipo, uf, _chave_nome(p.nome_civil or ""))) or por_nome.get(
            (tipo, uf, "urna:" + _chave_nome(p.nome or ""))) or por_nome.get((tipo, uf, _chave_nome(p.nome or ""))) or []
        if not achadas:
            continue
        cpfs = {c.cpf for c in achadas if c.cpf}
        if len(cpfs) > 1 or (not cpfs and len({c.ano for c in achadas}) < len(achadas)):
            ambiguos += 1
            continue
        todas = {c.sq: c for c in achadas}
        if cpfs:
            for c in por_cpf[next(iter(cpfs))]:
                todas[c.sq] = c
        saida[(p.casa, p.codigo)] = sorted(todas.values(), key=lambda c: (c.ano, c.sq))
    if ambiguos:
        logger.info("Ocorrências: %s políticos com nome ambíguo no TSE ficaram sem cruzamento", ambiguos)
    return saida


def ocorrencias_tse(cands: List[Candidatura]) -> List[Dict[str, Any]]:
    itens = []
    for c in cands:
        if c.detalhe in DETALHES_TSE:
            situacao, titulo = DETALHES_TSE[c.detalhe]
            desc = f"Eleição de {c.ano}, cargo de {c.cargo.lower()} ({c.uf})."
            if c.motivos:
                desc += " Motivo registrado pelo TSE: " + "; ".join(c.motivos) + "."
            itens.append({"fonte": "tse", "tipo": "candidatura", "titulo": f"{titulo} ({c.ano})", "descricao": desc,
                          "situacao": situacao, "data": None,
                          "orgao": "Justiça Eleitoral", "processo": None, "link": c.link, "conferencia": CONFERIDO_TSE})
        elif c.motivos:
            itens.append({"fonte": "tse", "tipo": "candidatura", "titulo": f"Motivo de cassação registrado ({c.ano})",
                          "descricao": "; ".join(c.motivos), "situacao": "informativo", "data": None,
                          "orgao": "Justiça Eleitoral", "processo": None, "link": c.link, "conferencia": CONFERIDO_TSE})
    return itens


def certidoes(cands: List[Candidatura]) -> List[Dict[str, Any]]:
    """Link da página de cada candidatura, onde estão as certidões criminais."""
    return [{"fonte": "tse", "tipo": "certidoes", "titulo": f"Certidões criminais entregues ao TSE ({c.ano})",
             "descricao": f"Candidatura a {c.cargo.lower()} ({c.uf})", "situacao": "informativo", "data": None,
             "orgao": "Tribunal Superior Eleitoral", "processo": None, "link": c.link, "conferencia": CONFERIDO_TSE}
            for c in cands]


# --- CGU (CEIS e CNEP) ---------------------------------------------------------------------


def ler_sancoes_pf(linhas: Iterable[Dict[str, str]]) -> Dict[str, List[Dict[str, Any]]]:
    """Chave do nome -> sanções a pessoas físicas, com o CPF mascarado só para conferir."""
    por_nome: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for l in linhas:
        if (l.get("TIPO DE PESSOA") or "").strip().upper() != "F":
            continue
        nome = l.get("NOME DO SANCIONADO") or l.get("NOME INFORMADO PELO ÓRGÃO SANCIONADOR") or ""
        cadastro = (l.get("CADASTRO") or "CEIS").strip().upper()
        por_nome[_chave_nome(nome)].append({
            "_cpf": (l.get("CPF OU CNPJ DO SANCIONADO") or "").strip(),
            "cadastro": cadastro,
            "categoria": (l.get("CATEGORIA DA SANÇÃO") or "").strip(),
            "inicio": _data_br(l.get("DATA INÍCIO SANÇÃO")),
            "fim": _data_br(l.get("DATA FINAL SANÇÃO")),
            "transito": _data_br(l.get("DATA DO TRÂNSITO EM JULGADO")),
            "orgao": (l.get("ÓRGÃO SANCIONADOR") or "").strip() or None,
            "processo": (l.get("NÚMERO DO PROCESSO") or "").strip() or None,
            "fundamento": (l.get("FUNDAMENTAÇÃO LEGAL") or "").strip(),
        })
    return por_nome


def ocorrencias_cgu(sancoes: List[Dict[str, Any]], hoje: date) -> List[Dict[str, Any]]:
    itens = []
    for s in sancoes:
        vigente = s["fim"] is None or s["fim"] >= hoje
        partes = []  # a data de início já vai no campo "data"
        if s["fim"]:
            partes.append(f"{'Termina' if vigente else 'Terminou'} em {s['fim']:%d/%m/%Y}")
        if s["transito"]:
            partes.append(f"decisão definitiva (trânsito em julgado) em {s['transito']:%d/%m/%Y}")
        desc = ", ".join(partes)
        desc = desc[:1].upper() + desc[1:]
        if s["fundamento"]:
            desc = (desc + ". " if desc else "") + f"Fundamento: {s['fundamento'][:200]}"
        itens.append({
            "fonte": "cgu", "tipo": "sancao",
            "titulo": f"{s['categoria'] or 'Sanção'} ({s['cadastro']})",
            "descricao": desc or None,
            "situacao": "sancao_vigente" if vigente else "sancao_encerrada",
            "data": s["inicio"], "orgao": s["orgao"], "processo": s["processo"],
            "link": SANCOES_PAGINA.format(cadastro=s["cadastro"].lower()), "conferencia": CONFERIDO_CPF,
        })
    return itens


def baixar_sancoes(client: HttpClient, hoje: date) -> Optional[Tuple[Dict[str, List[Dict[str, Any]]], date]]:
    """CEIS e CNEP do dia mais recente publicado (até 7 dias atrás)."""
    for atraso in range(1, 8):
        dia = hoje - timedelta(days=atraso)
        try:
            por_nome: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for cadastro in ("ceis", "cnep"):
                conteudo = client.get_bytes(SANCOES_URL.format(cadastro=cadastro, data=dia.strftime("%Y%m%d")))
                if not zipfile.is_zipfile(io.BytesIO(conteudo)):
                    raise RuntimeError(f"{cadastro} de {dia} não é um zip")
                for nome, lista in ler_sancoes_pf(_csvs(conteudo)).items():
                    por_nome[nome].extend(lista)
        except Exception as e:  # noqa: BLE001 - tenta o dia anterior
            logger.info("CEIS/CNEP de %s indisponíveis: %s", dia, e)
            continue
        logger.info("CEIS/CNEP de %s: %s nomes de pessoas físicas", dia, len(por_nome))
        return dict(por_nome), dia
    logger.warning("CEIS/CNEP não baixados")
    return None


# --- TCU -----------------------------------------------------------------------------------


def _campo(item: Dict[str, Any], *nomes: str) -> Optional[str]:
    for n in nomes:
        for k, v in item.items():
            if k.lower() == n and v not in (None, ""):
                return str(v).strip()
    return None


def baixar_tcu(client: HttpClient, max_paginas: int = 200) -> List[Dict[str, Any]]:
    """Inabilitados do TCU (serviço ORDS, paginado por offset)."""
    itens: List[Dict[str, Any]] = []
    offset = 0
    for _ in range(max_paginas):
        dados = client.get_json(TCU_URL, {"offset": offset} if offset else None)
        lote = dados.get("items", []) if isinstance(dados, dict) else list(dados or [])
        itens.extend(lote)
        if not (isinstance(dados, dict) and dados.get("hasMore")) or not lote:
            break
        offset += len(lote)
    logger.info("TCU: %s inabilitados", len(itens))
    return itens


def ler_tcu(itens: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    por_nome: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for i in itens:
        nome = _campo(i, "nome", "nome_responsavel")
        if not nome:
            continue
        por_nome[_chave_nome(nome)].append({
            "_cpf": _campo(i, "cpf", "cpf_responsavel", "num_cpf") or "",
            "processo": _campo(i, "processo", "num_processo"),
            "deliberacao": _campo(i, "deliberacao", "acordao"),
            "transito": _data_br(_campo(i, "data_transito_julgado", "transito_julgado")),
            "fim": _data_br(_campo(i, "data_final", "data_fim")),
            "acordao": _data_br(_campo(i, "data_acordao")),
        })
    return por_nome


def ocorrencias_tcu(registros: List[Dict[str, Any]], hoje: date) -> List[Dict[str, Any]]:
    itens = []
    for r in registros:
        vigente = r["fim"] is None or r["fim"] >= hoje
        partes = []
        if r["deliberacao"]:
            partes.append(f"Deliberação {r['deliberacao']}")
        if r["transito"]:
            partes.append(f"decisão definitiva em {r['transito']:%d/%m/%Y}")
        if r["fim"]:
            partes.append(f"{'vale' if vigente else 'valeu'} até {r['fim']:%d/%m/%Y}")
        itens.append({
            "fonte": "tcu", "tipo": "inabilitacao",
            "titulo": "Inabilitado pelo TCU para cargo em comissão ou função de confiança",
            "descricao": ", ".join(partes) or None,
            "situacao": "sancao_vigente" if vigente else "sancao_encerrada",
            "data": r["transito"] or r["acordao"], "orgao": "Tribunal de Contas da União",
            "processo": r["processo"], "link": TCU_PAGINA, "conferencia": CONFERIDO_CPF,
        })
    return itens


# --- coleta --------------------------------------------------------------------------------


def _por_cpf(por_nome: Dict[str, List[Dict[str, Any]]], nomes: Set[str], cpf: Optional[str]) -> List[Dict[str, Any]]:
    """Registros com nome igual a um dos nomes da pessoa e CPF conferido."""
    if not cpf:
        return []
    return [r for n in nomes for r in por_nome.get(n, []) if cpf_confere(r["_cpf"], cpf)]


def coletar(client: HttpClient, anos: Iterable[int] = ANOS_TSE, hoje: Optional[date] = None) -> int:
    hoje = hoje or date.today()
    with sessao() as s:
        politicos = s.execute(select(Politico)).scalars().all()
    candidaturas: List[Candidatura] = []
    for ano in anos:
        lista = ler_candidaturas(client.get_bytes(CANDIDATOS_URL.format(ano=ano)), ano)
        try:
            motivos = ler_motivos(client.get_bytes(MOTIVO_CASSACAO_URL.format(ano=ano)))
        except Exception as e:  # noqa: BLE001 - o arquivo de motivos é complemento
            logger.warning("Motivos de cassação de %s indisponíveis: %s", ano, e)
            motivos = {}
        for c in lista:
            c.motivos = motivos.get(c.sq, [])
        logger.info("TSE %s: %s candidaturas, %s com CPF, %s com motivo de cassação",
                    ano, len(lista), sum(1 for c in lista if c.cpf), sum(1 for c in lista if c.motivos))
        candidaturas.extend(lista)
    casadas = casar_candidaturas(politicos, candidaturas)
    cpf_de = {k: next((c.cpf for c in v if c.cpf), None) for k, v in casadas.items()}
    nomes_de = {k: {c.nome for c in v} for k, v in casadas.items()}
    logger.info("Ocorrências: %s de %s políticos achados no TSE, %s com CPF para conferir",
                len(casadas), len(politicos), sum(1 for v in cpf_de.values() if v))

    itens: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for k, cands in casadas.items():
        itens[k] += ocorrencias_tse(cands) + certidoes(cands)
    consultas = [ConsultaOcorrencia(fonte="tse", consultado_em=hoje, registros=len(candidaturas), conferidos=len(casadas))]

    try:
        sancoes = baixar_sancoes(client, hoje)
    except Exception as e:  # noqa: BLE001
        logger.warning("CEIS/CNEP: %s", e)
        sancoes = None
    if sancoes:
        por_nome, dia = sancoes
        for k in casadas:
            itens[k] += ocorrencias_cgu(_por_cpf(por_nome, nomes_de[k], cpf_de[k]), hoje)
        consultas.append(ConsultaOcorrencia(fonte="cgu", consultado_em=dia, registros=sum(map(len, por_nome.values())),
                                            conferidos=sum(1 for v in cpf_de.values() if v)))
    try:
        tcu = ler_tcu(baixar_tcu(client))
    except Exception as e:  # noqa: BLE001
        logger.warning("TCU indisponível: %s", e)
        tcu = None
    if tcu is not None:
        for k in casadas:
            itens[k] += ocorrencias_tcu(_por_cpf(tcu, nomes_de[k], cpf_de[k]), hoje)
        consultas.append(ConsultaOcorrencia(fonte="tcu", consultado_em=hoje, registros=sum(map(len, tcu.values())),
                                            conferidos=sum(1 for v in cpf_de.values() if v)))

    fontes = [c.fonte for c in consultas]
    total = 0
    with sessao() as s:
        s.execute(delete(Ocorrencia))
        s.execute(delete(ConsultaOcorrencia))
        s.execute(delete(VerificacaoOcorrencia))
        for (casa, codigo) in casadas:
            for fonte in fontes:
                if fonte == "tse" or cpf_de[(casa, codigo)]:
                    s.add(VerificacaoOcorrencia(casa=casa, codigo_politico=codigo, fonte=fonte))
        for (casa, codigo), lista in itens.items():
            for i in lista:
                s.add(Ocorrencia(casa=casa, codigo_politico=codigo, **i))
                total += i["tipo"] != "certidoes"
        s.add_all(consultas)
    logger.info("Ocorrências gravadas: %s (fora os links de certidões), fontes: %s",
                total, ", ".join(c.fonte for c in consultas))
    return total
