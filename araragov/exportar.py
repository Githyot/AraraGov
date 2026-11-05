"""Exporta o banco como uma API estática (arquivos JSON) para o app ler.

Estrutura gerada em <saida>/v1/:
  meta.json                     data da geração e fontes
  politicos.json                lista resumida de todos os políticos
  politicos/{casa}-{codigo}.json perfil completo de cada um

Arquivos estáticos podem ser servidos de graça (GitHub Pages) e ficam em
cache no celular, então o app abre rápido mesmo com internet ruim.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from . import __version__
from .analise import espectro, inflacao
from .analise.atencao import motivo_atencao
from .db import Assessor, Beneficio, Despesa, Emenda, Favorecido, Politico, RecursoMensal, Subsidio, Votacao, Voto, sessao

logger = logging.getLogger(__name__)

FONTES = {
    "camara": "https://dadosabertos.camara.leg.br",
    "senado": "https://legis.senado.leg.br/dadosabertos",
    "ipca": "https://www.bcb.gov.br (série SGS 433)",
    "tse": "https://dadosabertos.tse.jus.br (candidatos eleitos)",
    "emendas": "https://portaldatransparencia.gov.br/emendas",
    "al-mg": "https://dadosabertos.almg.gov.br",
    "al-sp": "https://www.al.sp.gov.br/dados-abertos",
}

# Constituição, art. 27, § 2º: o subsídio do deputado estadual é de no máximo
# 75% do deputado federal. Quase todas as assembleias pagam o teto, mas cada
# uma fixa o valor por lei própria, então o app mostra isso como teto.
FRACAO_ESTADUAL = Decimal("0.75")
CARGOS_ESTADUAIS = {"Deputado estadual", "Deputado distrital"}
OBS_ESTADUAL = (
    "Teto constitucional: 75% do subsídio de deputado federal (CF, art. 27, § 2º). "
    "O valor exato é fixado por lei de cada assembleia."
)
OBS_GOVERNO = "Fixado por lei estadual; ainda não coletado."

# Cadastros que vêm da lista de eleitos do TSE (fonte="tse") recebem um aviso.
AVISO_TSE = (
    "Dados da eleição de 2022 (TSE). Suplentes que assumiram depois e trocas "
    "de partido podem não aparecer."
)


def _json(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    raise TypeError(type(valor))


def _gravar(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, default=_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def orgao(casa: str) -> Dict[str, str]:
    """Esfera e nome do órgão, para filtros e títulos no app."""
    if casa == "camara":
        return {"esfera": "federal", "orgao": "Câmara dos Deputados"}
    if casa == "senado":
        return {"esfera": "federal", "orgao": "Senado Federal"}
    prefixo, _, uf = casa.partition("-")
    uf = uf.upper()
    if prefixo == "al":
        nome = "Câmara Legislativa do DF" if uf == "DF" else f"Assembleia Legislativa ({uf})"
        return {"esfera": "estadual", "orgao": nome}
    if prefixo == "gov":
        return {"esfera": "estadual", "orgao": f"Governo do estado ({uf})"}
    return {"esfera": "outra", "orgao": casa}


DOACOES_CSV = Path(__file__).parent / "referencia" / "doacao_salario.csv"


def doacoes_salario(caminho: Path = DOACOES_CSV) -> Dict[tuple, Dict[str, Any]]:
    """Políticos que declaram publicamente doar o salário (ou parte dele).

    Lista curada à mão: cada linha precisa de uma fonte pública (fala do
    próprio político ou reportagem). O app mostra como "declara doar", sem
    afirmar que a doação foi conferida."""
    import csv
    from .collectors.gabinete import _chave_nome

    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    return {
        (l["casa"].strip(), _chave_nome(l["nome"])): {
            "parte": (l.get("parte") or "").strip() or None,
            "descricao": l["descricao"].strip(),
            "fonte": l["fonte"].strip(),
            "data": (l.get("data") or "").strip() or None,
        }
        for l in linhas
        if (l.get("fonte") or "").strip().startswith("http")
    }


IDEOLOGIA_PARTIDOS_CSV = Path(__file__).parent / "referencia" / "ideologia_partidos.csv"
IDEOLOGIA_POLITICOS_CSV = Path(__file__).parent / "referencia" / "ideologia_politicos.csv"


def _ler_curado(caminho: Path) -> List[Dict[str, str]]:
    """Lê uma lista curada (CSV com ;); linhas sem link de fonte são ignoradas."""
    import csv

    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as f:
        return [
            {k: (v or "").strip() for k, v in l.items()}
            for l in csv.DictReader(f, delimiter=";")
            if (l.get("fonte") or "").strip().startswith("http")
        ]


def ideologias_declaradas() -> Tuple[Dict[str, Dict[str, str]], Dict[tuple, Dict[str, str]]]:
    """O que partidos e políticos declaram sobre a própria ideologia, nas
    palavras deles (estatuto, programa, carta, entrevista), com a fonte.
    Serve para comparar com a posição medida pelos votos, sem julgamento."""
    from .collectors.gabinete import _chave_nome

    campos = ("declaracao", "trecho", "documento", "fonte")
    partidos = {l["partido"].upper(): {k: l[k] or None for k in campos} for l in _ler_curado(IDEOLOGIA_PARTIDOS_CSV)}
    politicos = {
        (l["casa"], _chave_nome(l["nome"])): {k: l[k] or None for k in campos}
        for l in _ler_curado(IDEOLOGIA_POLITICOS_CSV)
    }
    return partidos, politicos


def _ideologia(p: Politico, declaradas) -> Optional[Dict[str, Any]]:
    from .collectors.gabinete import _chave_nome

    partidos, politicos = declaradas
    partido = partidos.get((p.partido or "").upper())
    pessoal = politicos.get((p.casa, _chave_nome(p.nome or "")))
    if not partido and not pessoal:
        return None
    return {"partido": partido, "pessoal": pessoal}


def _doacao(p: Politico, doacoes: Dict[tuple, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    from .collectors.gabinete import _chave_nome

    return doacoes.get((p.casa, _chave_nome(p.nome or "")))


VOTOS_INLINE = 8


def _dia(valor: Any) -> Optional[str]:
    return valor.isoformat()[:10] if valor else None


def _detalhe(votacao: Votacao, analises: Dict[Any, Any]) -> Dict[str, Any]:
    return {
        "data": votacao.data,
        "proposicao": votacao.proposicao,
        "descricao": votacao.descricao,
        "ementa": votacao.ementa,
        "resultado": votacao.resultado,
        "link": votacao.link,
        "lado_sim": analises["_lados"].get(votacao.id),
        "atencao": analises["_atencao"].get(votacao.id),
    }


def _detalhe_voto(v: Voto, votacao: Votacao, analises: Dict[Any, Any]) -> Dict[str, Any]:
    return {"id": v.votacao_id, **_detalhe(votacao, analises), "voto": v.voto, "partido_na_epoca": v.partido}


def _resumo(p: Politico, doacoes: Optional[Dict[tuple, Dict[str, Any]]] = None) -> Dict[str, Any]:
    return {
        "id": f"{p.casa}-{p.codigo}",
        "casa": p.casa,
        **orgao(p.casa),
        "cargo": p.cargo,
        "nome": p.nome,
        "partido": p.partido,
        "uf": p.uf,
        "foto": p.url_foto,
        "em_exercicio": bool(p.em_exercicio),
        "doa_salario": bool(doacoes and _doacao(p, doacoes)),
    }


def _salario(cargo: str, subsidios: List[Subsidio]) -> Dict[str, Any]:
    if cargo in CARGOS_ESTADUAIS:
        federal = _salario("Deputado Federal", subsidios)

        def fator(valor):
            return (Decimal(valor) * FRACAO_ESTADUAL).quantize(Decimal("0.01"))

        resultado = {
            "atual": fator(federal["atual"]) if federal["atual"] is not None else None,
            "historico": [{**h, "valor": fator(h["valor"])} for h in federal["historico"]],
            "teto": True,
            "observacao": OBS_ESTADUAL,
        }
        if "vs_inflacao" in federal:
            vs = dict(federal["vs_inflacao"])
            for k in ("valor_inicial", "valor_atual", "corrigido_pela_inflacao"):
                vs[k] = fator(vs[k])
            resultado["vs_inflacao"] = vs
        return resultado
    if cargo in ("Governador", "Vice-governador"):
        return {"atual": None, "historico": [], "observacao": OBS_GOVERNO}
    historico = [
        {"desde": s.vigencia_inicio, "valor": s.valor, "ato": s.ato, "fonte": s.fonte}
        for s in sorted(subsidios, key=lambda s: s.vigencia_inicio)
        if s.cargo == cargo
    ]
    resultado: Dict[str, Any] = {"atual": historico[-1]["valor"] if historico else None, "historico": historico}
    if len(historico) >= 2:
        comp = inflacao.subsidio_vs_inflacao(cargo, historico[0]["desde"], historico[-1]["desde"])
        if comp:
            resultado["vs_inflacao"] = {
                "desde": comp.referencia,
                "valor_inicial": comp.valor_referencia,
                "valor_atual": comp.valor_real,
                "corrigido_pela_inflacao": comp.valor_corrigido,
                "acima_da_inflacao_pct": round(comp.acima_da_inflacao_pct, 2),
            }
    return resultado


def _resumo_emendas(emendas: List[Emenda], favorecidos: List[Favorecido]) -> Dict[str, Any]:
    por_area: Dict[str, Decimal] = defaultdict(Decimal)
    por_local: Dict[str, Decimal] = defaultdict(Decimal)
    for e in emendas:
        por_area[e.funcao or "Não informada"] += e.empenhado
        por_local[e.localidade or "Não informado"] += e.empenhado
    receb: Dict[tuple, Decimal] = defaultdict(Decimal)
    meta: Dict[tuple, Favorecido] = {}
    for f in favorecidos:
        chave = (f.nome, f.documento)
        receb[chave] += f.valor
        meta.setdefault(chave, f)

    def top(d: Dict[str, Decimal], k: int = 8) -> List[Dict[str, Any]]:
        return [{"nome": nome, "valor": v} for nome, v in sorted(d.items(), key=lambda x: -x[1])[:k]]

    return {
        "total_empenhado": sum((e.empenhado for e in emendas), Decimal(0)),
        "total_pago": sum((e.pago for e in emendas), Decimal(0)),
        "quantidade": len(emendas),
        "por_area": top(por_area),
        "por_local": top(por_local),
        "favorecidos": [
            {"nome": nome, "documento": doc, "tipo": meta[(nome, doc)].tipo,
             "municipio": meta[(nome, doc)].municipio, "uf": meta[(nome, doc)].uf, "valor": v}
            for (nome, doc), v in sorted(receb.items(), key=lambda x: -x[1])[:10]
        ],
    }


def _emendas(emendas: List[Emenda], favorecidos: List[Favorecido]) -> Optional[Dict[str, Any]]:
    """Resumo das emendas do parlamentar: quanto indicou, quanto foi pago,
    para quais áreas e lugares, e quem recebeu o dinheiro. Também por ano,
    para o filtro de período do app."""
    if not emendas:
        return None
    anos = sorted({e.ano for e in emendas})
    por_ano_resumo = {
        a: _resumo_emendas([e for e in emendas if e.ano == a], [f for f in favorecidos if f.ano == a]) for a in anos
    }
    return {
        **_resumo_emendas(emendas, favorecidos),
        "por_ano": [
            {"ano": a, "empenhado": r["total_empenhado"], "pago": r["total_pago"]} for a, r in por_ano_resumo.items()
        ],
        "anos": {str(a): r for a, r in por_ano_resumo.items()},
    }


def _mensais(linhas: List[RecursoMensal]) -> Optional[Dict[str, Any]]:
    """Valores mensais (salário pago, verba de gabinete) somados por ano."""
    if not linhas:
        return None
    anos: Dict[int, List[RecursoMensal]] = defaultdict(list)
    for l in linhas:
        anos[l.ano].append(l)
    return {
        "total": sum((l.valor for l in linhas), Decimal(0)),
        "por_ano": [{"ano": a, "valor": sum((l.valor for l in anos[a]), Decimal(0))} for a in sorted(anos)],
        "anos": {
            str(a): {
                "total": sum((l.valor for l in anos[a]), Decimal(0)),
                "por_mes": [{"mes": l.mes, "valor": l.valor} for l in sorted(anos[a], key=lambda x: x.mes)],
            }
            for a in sorted(anos)
        },
    }


def _ultimo_mes(linhas: List[RecursoMensal]) -> Optional[RecursoMensal]:
    com_valor = [l for l in linhas if l.valor > 0]
    return max(com_valor, key=lambda l: (l.ano, l.mes)) if com_valor else None


def _beneficios_por_ano(itens: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Benefícios sem ano (retrato do mês) mais os do ano mais recente; e
    todos os anos separados, para o filtro de período do app."""
    sem_ano = [b for b in itens if b.get("ano") is None]
    anos: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for b in itens:
        if b.get("ano") is not None:
            anos[b["ano"]].append(b)
    atuais = sem_ano + (anos[max(anos)] if anos else [])
    return atuais, {str(a): sem_ano + anos[a] for a in sorted(anos)}


def _custo_gabinete(pessoas: List[Dict[str, Any]], verba: Optional[RecursoMensal] = None) -> Optional[Dict[str, Any]]:
    """Custo mensal do gabinete: soma das remunerações, quando a casa publica
    (Senado), ou a verba de gabinete gasta no último mês (Câmara)."""
    com_valor = [p for p in pessoas if p.get("remuneracao") is not None]
    if not com_valor:
        if verba is None:
            return None
        return {
            "mensal": verba.valor,
            "pessoas_com_valor": 0,
            "pessoas": len(pessoas),
            "referencia": f"{verba.ano}-{verba.mes:02d}",
            "origem": "verba_gabinete",
        }
    return {
        "mensal": sum((p["remuneracao"] for p in com_valor), Decimal(0)),
        "pessoas_com_valor": len(com_valor),
        "pessoas": len(pessoas),
        "referencia": com_valor[0].get("remuneracao_ref"),
        "origem": "folha",
    }


def _gastos(despesas: List[Despesa], politico: Politico) -> Dict[str, Any]:
    por_ano: Dict[int, Decimal] = defaultdict(Decimal)
    por_mes: Dict[str, Decimal] = defaultdict(Decimal)
    por_categoria: Dict[str, Decimal] = defaultdict(Decimal)
    por_fornecedor: Dict[str, Decimal] = defaultdict(Decimal)
    # Para o filtro de período do app: categoria e fornecedor de cada ano.
    cat_ano: Dict[int, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    forn_ano: Dict[int, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for d in despesas:
        cat_ano[d.ano][d.categoria or "Outros"] += d.valor
        forn_ano[d.ano][d.fornecedor or "Não informado"] += d.valor
        por_ano[d.ano] += d.valor
        por_mes[f"{d.ano}-{d.mes:02d}"] += d.valor
        por_categoria[d.categoria or "Outros"] += d.valor
        por_fornecedor[d.fornecedor or "Não informado"] += d.valor
    vs_inflacao = [
        {
            "ano": c.data.year,
            "desde": c.referencia,
            "valor_inicial": c.valor_referencia,
            "valor": c.valor_real,
            "corrigido_pela_inflacao": c.valor_corrigido,
            "acima_da_inflacao_pct": round(c.acima_da_inflacao_pct, 2),
        }
        for c in inflacao.gastos_vs_inflacao(politico.casa, politico.codigo)
    ]
    top = lambda d, n: [{"nome": k, "valor": v} for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
    return {
        "total": sum(por_ano.values(), Decimal(0)),
        "por_ano": [{"ano": a, "valor": v} for a, v in sorted(por_ano.items())],
        "por_mes": [{"mes": m, "valor": v} for m, v in sorted(por_mes.items())],
        "por_categoria": top(por_categoria, 20),
        "maiores_fornecedores": top(por_fornecedor, 10),
        "anos": {
            str(a): {"total": por_ano[a], "por_categoria": top(cat_ano[a], 20), "maiores_fornecedores": top(forn_ano[a], 10)}
            for a in sorted(por_ano)
        },
        "vs_inflacao": vs_inflacao,
        "documentos_recentes": [
            {
                "data": d.data_documento,
                "categoria": d.categoria,
                "fornecedor": d.fornecedor,
                "valor": d.valor,
                "url": d.url_documento,
            }
            for d in sorted(despesas, key=lambda d: (d.ano, d.mes), reverse=True)[:30]
        ],
    }


def _analises(politicos, votos_por, votacoes) -> Dict[Any, Any]:
    """Posição no espectro, alinhamento com partidos e votações de atenção."""
    saida: Dict[Any, Any] = {"_lados": {}, "_atencao": {}}
    for vid, v in votacoes.items():
        motivo = motivo_atencao(v.ementa, v.descricao)
        if motivo:
            saida["_atencao"][vid] = motivo

    partido_atual = {(p.casa, p.codigo): p.partido for p in politicos}
    for casa in ("camara", "senado"):
        simples = [
            espectro.VotoSimples(v.votacao_id, v.codigo_politico, v.partido, v.voto)
            for (c, _), lista in votos_por.items()
            if c == casa
            for v in lista
        ]
        if not simples:
            continue
        r = espectro.calcular(simples)
        n_votacoes = len({v.votacao_id for v in simples})
        logger.info(
            "%s: %s votos em %s votações (%.1f por votação), %s com partido",
            casa, len(simples), n_votacoes, len(simples) / n_votacoes,
            sum(1 for v in simples if v.partido),
        )
        for vid, lado in r.votacoes.items():
            saida["_lados"][vid] = lado.lado_sim
        alinh = espectro.alinhamento_partidos(simples)
        logger.info(
            "%s: %s votações ideológicas (esquerda x direita), %s parlamentares posicionados",
            casa, len(r.votacoes), len(r.pct_esquerda),
        )

        por_partido: Dict[str, List[float]] = defaultdict(list)
        for cod, (pct, _) in r.pct_esquerda.items():
            partido = partido_atual.get((casa, cod))
            if partido:
                por_partido[partido].append(pct)

        medias = sorted(
            ((sum(v) / len(v), k, len(v)) for k, v in por_partido.items() if len(v) >= 3), reverse=True
        )
        logger.info(
            "%s: %% médio à esquerda por partido: %s",
            casa, ", ".join(f"{k} {m:.0f}% (n={n})" for m, k, n in medias),
        )
        for (c, cod), lista in votos_por.items():
            if c != casa:
                continue
            item: Dict[str, Any] = {}
            if cod in r.pct_esquerda:
                pct, n = r.pct_esquerda[cod]
                partido = partido_atual.get((casa, cod))
                media = por_partido.get(partido or "")
                item["posicao"] = {
                    "pct_esquerda": pct,
                    "pct_direita": round(100 - pct, 1),
                    "faixa": espectro.faixa(pct),
                    "votacoes_consideradas": n,
                    "media_do_partido": round(sum(media) / len(media), 1) if media else None,
                    "faixa_do_partido": espectro.faixa(sum(media) / len(media)) if media else None,
                }
            if cod in alinh:
                partido = (partido_atual.get((casa, cod)) or "").upper().replace(" ", "")
                todos = alinh[cod]
                item["alinhamento"] = {
                    "mais_alinhados": todos[:5],
                    "menos_alinhados": todos[-3:][::-1] if len(todos) > 5 else [],
                    "proprio_partido": next((a for a in todos if a["partido"] == partido), None),
                }
            de_atencao = [v for v in lista if v.votacao_id in saida["_atencao"]]
            if de_atencao:
                item["atencao"] = {
                    "votacoes": len(de_atencao),
                    "votou_sim": sum(1 for v in de_atencao if v.voto == "sim"),
                    "votou_nao": sum(1 for v in de_atencao if v.voto == "nao"),
                }
            saida[(casa, cod)] = item
    return saida


def exportar(saida: Path) -> int:
    base = saida / "v1"
    with sessao() as s:
        politicos = s.execute(select(Politico).order_by(Politico.nome)).scalars().all()
        subsidios = s.execute(select(Subsidio)).scalars().all()
        votacoes = {v.id: v for v in s.execute(select(Votacao)).scalars()}
        votos_por = defaultdict(list)
        for v in s.execute(select(Voto)).scalars():
            votos_por[(v.casa, v.codigo_politico)].append(v)
        despesas_por = defaultdict(list)
        for d in s.execute(select(Despesa).where(Despesa.codigo_politico.is_not(None))).scalars():
            despesas_por[(d.casa, d.codigo_politico)].append(d)

        gabinetes = defaultdict(list)
        for a in s.execute(select(Assessor).where(Assessor.codigo_politico.is_not(None)).order_by(Assessor.nome)).scalars():
            gabinetes[(a.casa, a.codigo_politico)].append(
                {
                    "nome": a.nome, "cargo": a.cargo, "nivel": a.funcao, "desde": a.desde,
                    "remuneracao": a.remuneracao, "remuneracao_ref": a.remuneracao_ref,
                }
            )
        emendas_por = defaultdict(list)
        for e in s.execute(select(Emenda).where(Emenda.codigo_politico.is_not(None))).scalars():
            emendas_por[(e.casa, e.codigo_politico)].append(e)
        favorecidos_por = defaultdict(list)
        for f in s.execute(select(Favorecido)).scalars():
            favorecidos_por[(f.casa, f.codigo_politico)].append(f)
        beneficios = defaultdict(list)
        for b in s.execute(select(Beneficio).order_by(Beneficio.tipo)).scalars():
            beneficios[(b.casa, b.codigo_politico)].append(
                {"tipo": b.tipo, "descricao": b.descricao, "valor_mensal": b.valor_mensal,
                 "valor_ano": b.valor_ano, "ano": b.ano, "referencia": b.referencia, "fonte": b.fonte}
            )
        recursos = defaultdict(lambda: defaultdict(list))
        for r in s.execute(select(RecursoMensal)).scalars():
            recursos[(r.casa, r.codigo_politico)][r.tipo].append(r)

    analises = _analises(politicos, votos_por, votacoes)
    salarios = {cargo: _salario(cargo, subsidios) for cargo in {p.cargo for p in politicos}}
    doacoes = doacoes_salario()
    declaradas = ideologias_declaradas()

    for p in politicos:
        ben_atuais, ben_anos = _beneficios_por_ano(beneficios[(p.casa, p.codigo)])
        votos = sorted(
            votos_por[(p.casa, p.codigo)],
            key=lambda v: votacoes[v.votacao_id].data or datetime.min,
            reverse=True,
        )
        perfil = {
            **_resumo(p, doacoes),
            "doacao_salario": _doacao(p, doacoes),
            "ideologia_declarada": _ideologia(p, declaradas),
            "aviso_cadastro": AVISO_TSE if p.fonte == "tse" else None,
            "nome_civil": p.nome_civil,
            "email": p.email,
            "salario": salarios[p.cargo],
            "gastos": _gastos(despesas_por[(p.casa, p.codigo)], p),
            "gabinete": gabinetes[(p.casa, p.codigo)],
            "custo_gabinete": _custo_gabinete(
                gabinetes[(p.casa, p.codigo)], _ultimo_mes(recursos[(p.casa, p.codigo)]["verba_gabinete"])
            ),
            "verba_gabinete": _mensais(recursos[(p.casa, p.codigo)]["verba_gabinete"]),
            "salario_pago": _mensais(recursos[(p.casa, p.codigo)]["salario"]),
            "beneficios": ben_atuais,
            "beneficios_anos": ben_anos,
            "emendas": _emendas(emendas_por[(p.casa, p.codigo)], favorecidos_por[(p.casa, p.codigo)]),
            "presenca": dict(Counter(v.voto for v in votos)),
            **analises.get((p.casa, p.codigo), {}),
            # Todos os votos em formato compacto; detalhes de cada votação ficam
            # em votacoes/{ano}.json, compartilhados por todos os perfis.
            "votos_formato": ["id", "data", "voto", "lado_sim", "atencao"],
            "votos": [
                [
                    v.votacao_id,
                    _dia(votacoes[v.votacao_id].data),
                    v.voto,
                    analises["_lados"].get(v.votacao_id),
                    1 if analises["_atencao"].get(v.votacao_id) else 0,
                ]
                for v in votos
            ],
            # Detalhes inline só das mais recentes e das de atenção, para o
            # perfil abrir sem baixar mais nada.
            "votacoes": [
                _detalhe_voto(v, votacoes[v.votacao_id], analises)
                for i, v in enumerate(votos)
                if i < VOTOS_INLINE or analises["_atencao"].get(v.votacao_id)
            ],
        }
        _gravar(base / "politicos" / f"{p.casa}-{p.codigo}.json", perfil)

    por_ano: Dict[int, Dict[str, Any]] = defaultdict(dict)
    for vid, votacao in votacoes.items():
        if votacao.data:
            por_ano[votacao.data.year][vid] = _detalhe(votacao, analises)
    for ano, itens in por_ano.items():
        _gravar(base / "votacoes" / f"{ano}.json", itens)

    _gravar(base / "politicos.json", [_resumo(p, doacoes) for p in politicos])
    _gravar(
        base / "meta.json",
        {"gerado_em": datetime.now(timezone.utc), "versao": __version__, "total_politicos": len(politicos),
         "anos_votacoes": sorted(por_ano), "fontes": FONTES},
    )
    logger.info("Exportados %s políticos em %s", len(politicos), base)
    return len(politicos)
