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
from typing import Any, Dict, List

from sqlalchemy import select

from . import __version__
from .analise import espectro, inflacao
from .analise.atencao import motivo_atencao
from .db import Assessor, Despesa, Politico, Subsidio, Votacao, Voto, sessao

logger = logging.getLogger(__name__)

FONTES = {
    "camara": "https://dadosabertos.camara.leg.br",
    "senado": "https://legis.senado.leg.br/dadosabertos",
    "ipca": "https://www.bcb.gov.br (série SGS 433)",
    "tse": "https://dadosabertos.tse.jus.br (candidatos eleitos)",
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


def _resumo(p: Politico) -> Dict[str, Any]:
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


def _gastos(despesas: List[Despesa], politico: Politico) -> Dict[str, Any]:
    por_ano: Dict[int, Decimal] = defaultdict(Decimal)
    por_mes: Dict[str, Decimal] = defaultdict(Decimal)
    por_categoria: Dict[str, Decimal] = defaultdict(Decimal)
    por_fornecedor: Dict[str, Decimal] = defaultdict(Decimal)
    for d in despesas:
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
                {"nome": a.nome, "cargo": a.cargo, "nivel": a.funcao, "desde": a.desde}
            )

    analises = _analises(politicos, votos_por, votacoes)
    salarios = {cargo: _salario(cargo, subsidios) for cargo in {p.cargo for p in politicos}}

    for p in politicos:
        votos = sorted(
            votos_por[(p.casa, p.codigo)],
            key=lambda v: votacoes[v.votacao_id].data or datetime.min,
            reverse=True,
        )
        perfil = {
            **_resumo(p),
            "aviso_cadastro": AVISO_TSE if p.fonte == "tse" else None,
            "nome_civil": p.nome_civil,
            "email": p.email,
            "salario": salarios[p.cargo],
            "gastos": _gastos(despesas_por[(p.casa, p.codigo)], p),
            "gabinete": gabinetes[(p.casa, p.codigo)],
            "presenca": dict(Counter(v.voto for v in votos)),
            **analises.get((p.casa, p.codigo), {}),
            "votacoes": [
                {
                    "id": v.votacao_id,
                    "data": votacoes[v.votacao_id].data,
                    "proposicao": votacoes[v.votacao_id].proposicao,
                    "descricao": votacoes[v.votacao_id].descricao,
                    "ementa": votacoes[v.votacao_id].ementa,
                    "resultado": votacoes[v.votacao_id].resultado,
                    "link": votacoes[v.votacao_id].link,
                    "voto": v.voto,
                    "partido_na_epoca": v.partido,
                    "lado_sim": analises["_lados"].get(v.votacao_id),
                    "atencao": analises["_atencao"].get(v.votacao_id),
                }
                for v in votos
            ],
        }
        _gravar(base / "politicos" / f"{p.casa}-{p.codigo}.json", perfil)

    _gravar(base / "politicos.json", [_resumo(p) for p in politicos])
    _gravar(
        base / "meta.json",
        {"gerado_em": datetime.now(timezone.utc), "versao": __version__, "total_politicos": len(politicos), "fontes": FONTES},
    )
    logger.info("Exportados %s políticos em %s", len(politicos), base)
    return len(politicos)
