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
from .analise import inflacao
from .db import Assessor, Despesa, Politico, Subsidio, Votacao, Voto, sessao

logger = logging.getLogger(__name__)

FONTES = {
    "camara": "https://dadosabertos.camara.leg.br",
    "senado": "https://legis.senado.leg.br/dadosabertos",
    "ipca": "https://www.bcb.gov.br (série SGS 433)",
}


def _json(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    raise TypeError(type(valor))


def _gravar(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, default=_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _resumo(p: Politico) -> Dict[str, Any]:
    return {
        "id": f"{p.casa}-{p.codigo}",
        "casa": p.casa,
        "cargo": p.cargo,
        "nome": p.nome,
        "partido": p.partido,
        "uf": p.uf,
        "foto": p.url_foto,
        "em_exercicio": bool(p.em_exercicio),
    }


def _salario(cargo: str, subsidios: List[Subsidio]) -> Dict[str, Any]:
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

    salarios = {cargo: _salario(cargo, subsidios) for cargo in {p.cargo for p in politicos}}

    for p in politicos:
        votos = sorted(
            votos_por[(p.casa, p.codigo)],
            key=lambda v: votacoes[v.votacao_id].data or datetime.min,
            reverse=True,
        )
        perfil = {
            **_resumo(p),
            "nome_civil": p.nome_civil,
            "email": p.email,
            "salario": salarios[p.cargo],
            "gastos": _gastos(despesas_por[(p.casa, p.codigo)], p),
            "gabinete": gabinetes[(p.casa, p.codigo)],
            "presenca": dict(Counter(v.voto for v in votos)),
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
