"""Recursos e benefícios de cada deputado federal, por ano.

A página pública de cada deputado (https://www.camara.leg.br/deputados/{id})
reúne o que não está na API de dados abertos:

- verba de gabinete: quanto foi gasto por mês com os secretários parlamentares;
- imóvel funcional e auxílio-moradia (com o total recebido no ano);
- viagens em missão oficial e passaporte diplomático;
- salário bruto pago em cada mês (página /remuneracao).

As páginas de remuneração de cada secretário ficam em
/transparencia/recursos-humanos/remuneracao/, que o robots.txt da Câmara
pede para não coletar automaticamente; por isso o custo do gabinete vem da
verba de gabinete gasta, e não da soma dos salários individuais.
"""

from __future__ import annotations

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, insert, select

from ..db import Beneficio, Politico, RecursoMensal, sessao
from ..http import HttpClient

logger = logging.getLogger(__name__)

PAGINA = "https://www.camara.leg.br/deputados/{id}"
MESES = {m: i for i, m in enumerate("JAN FEV MAR ABR MAI JUN JUL AGO SET OUT NOV DEZ".split(), 1)}
CENTAVO = Decimal("0.01")
TRABALHOS = 4  # páginas baixadas em paralelo, para não sobrecarregar o site

# Anos antigos não mudam: com o histórico da coleta anterior carregado (ver
# historico.py), só buscamos os deputados que faltam, até este limite por
# execução. O histórico completa ao longo de algumas semanas.
ORCAMENTO_HISTORICO = 3000
_restante = {"valor": ORCAMENTO_HISTORICO}
MARCA = "coletado"  # linha de controle: deputado e ano já consultados


def _reais(texto: str) -> Optional[Decimal]:
    """ "R$ 29.771" -> 29771; "46.366,191" -> 46366.19."""
    t = re.sub(r"[^\d,]", "", texto or "")
    if not t:
        return None
    return Decimal(t.replace(",", ".")).quantize(CENTAVO, ROUND_HALF_UP)


def _limpo(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho)).split())


def _tabela(pagina: str, ident: str) -> List[List[str]]:
    m = re.search(rf'<table[^>]*id="{ident}".*?</table>', pagina, re.S)
    if not m:
        return []
    corpo = re.search(r"<tbody>(.*?)</tbody>", m.group(0), re.S)
    linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", corpo.group(1) if corpo else "", re.S)
    return [[_limpo(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", l, re.S)] for l in linhas]


def _beneficio(pagina: str, titulo: str) -> Optional[str]:
    """Texto do quadro de benefício com esse título ("Imóvel funcional"...)."""
    m = re.search(
        rf'<h3 class="beneficio__titulo">\s*{re.escape(titulo)}.*?</h3>(.*?)</div>', pagina, re.S
    )
    return _limpo(m.group(1)) if m else None


def ler_pagina(pagina: str, ano: int) -> Dict[str, Any]:
    """Extrai verba de gabinete e benefícios da página principal do deputado."""
    verba = []
    for linha in _tabela(pagina, "gastomensalverbagabinete"):
        if len(linha) >= 2 and linha[0].upper() in MESES:
            valor = _reais(linha[1])
            if valor is not None:
                verba.append((MESES[linha[0].upper()], valor))
    pessoas = _beneficio(pagina, "Pessoal de gabinete")
    viagens = _beneficio(pagina, "Viagens em missão oficial")
    return {
        "ano": ano,
        "verba_gabinete": verba,
        "pessoas": int(re.sub(r"\D", "", pessoas)) if pessoas and re.search(r"\d", pessoas) else None,
        "imovel": _beneficio(pagina, "Imóvel funcional"),
        "auxilio": _beneficio(pagina, "Auxílio-moradia"),
        "viagens": int(viagens) if viagens and viagens.isdigit() else None,
        "passaporte": _beneficio(pagina, "Passaporte diplomático"),
    }


def ler_remuneracao(pagina: str) -> List[Tuple[int, Decimal]]:
    """Salário bruto pago em cada mês (página /remuneracao?ano=)."""
    saida = []
    for mes, valor in re.findall(r'<td class="text-center">\s*(\d{2})\s*</td>\s*<td class="text-right">(.*?)</td>', pagina, re.S):
        v = _reais(_limpo(valor))
        if v is not None:
            saida.append((int(mes), v))
    return saida


def _beneficios(cod: int, dados: Dict[str, Any], fonte: str) -> List[Dict[str, Any]]:
    ano = dados["ano"]
    base = {"casa": "camara", "codigo_politico": cod, "ano": ano, "referencia": str(ano), "fonte": fonte, "valor_mensal": None, "valor_ano": None}
    saida = []
    imovel = dados.get("imovel") or ""
    if imovel and not imovel.lower().startswith("não"):
        saida.append({**base, "tipo": "imovel_funcional", "descricao": f"Imóvel funcional em Brasília: {imovel[0].lower()}{imovel[1:]}"})
    auxilio = dados.get("auxilio") or ""
    if auxilio.lower().startswith("recebeu"):
        saida.append({**base, "tipo": "auxilio_moradia", "descricao": "Recebeu auxílio-moradia", "valor_ano": _reais(auxilio)})
    if dados.get("viagens"):
        n = dados["viagens"]
        saida.append({**base, "tipo": "viagem_missao", "descricao": f"{n} viage{'m' if n == 1 else 'ns'} em missão oficial"})
    if (dados.get("passaporte") or "").lower().startswith("possui"):
        saida.append({**base, "tipo": "passaporte_diplomatico", "descricao": "Tem passaporte diplomático"})
    return saida


def coletar_recursos(client: HttpClient, ano: int, limite: Optional[int] = None, so_faltantes: bool = False) -> int:
    """Coleta os recursos do ano. Com `so_faltantes`, pula quem já foi
    consultado nesse ano e respeita o limite de páginas por execução."""
    with sessao() as s:
        consulta = select(Politico.codigo).where(Politico.casa == "camara").order_by(Politico.codigo)
        codigos = list(s.execute(consulta).scalars())
        feitos_antes = set()
        if so_faltantes:
            feitos_antes = set(
                s.execute(
                    select(RecursoMensal.codigo_politico).where(
                        RecursoMensal.casa == "camara", RecursoMensal.ano == ano, RecursoMensal.tipo == MARCA
                    )
                ).scalars()
            )
    if not codigos:
        raise RuntimeError("Nenhum deputado no banco. Rode antes: araragov coletar camara-deputados")
    if limite:
        codigos = codigos[:limite]
    if so_faltantes:
        codigos = [c for c in codigos if c not in feitos_antes][: max(_restante["valor"], 0)]
        _restante["valor"] -= len(codigos)
        if not codigos:
            logger.info("Câmara %s: recursos já no histórico (ou limite da execução atingido)", ano)
            return 0

    def um(cod: int):
        url = PAGINA.format(id=cod)
        try:
            principal = client.get_bytes(url, {"ano": ano}).decode("utf-8", "replace")
            salario = client.get_bytes(f"{url}/remuneracao", {"ano": ano}).decode("utf-8", "replace")
        except Exception as e:  # um deputado fora do ar não derruba os outros
            logger.warning("Câmara: página do deputado %s (%s) indisponível: %s", cod, ano, e)
            return cod, None, []
        return cod, ler_pagina(principal, ano), ler_remuneracao(salario)

    with ThreadPoolExecutor(TRABALHOS) as ex:
        resultados = list(ex.map(um, codigos))

    beneficios: List[Dict[str, Any]] = []
    mensais: List[Dict[str, Any]] = []
    ok = 0
    for cod, dados, salario in resultados:
        if dados is None:
            continue
        ok += 1
        fonte = f"{PAGINA.format(id=cod)}?ano={ano}"
        beneficios.extend(_beneficios(cod, dados, fonte))
        base = {"casa": "camara", "codigo_politico": cod, "ano": ano}
        mensais += [{**base, "tipo": "verba_gabinete", "mes": m, "valor": v, "disponivel": None} for m, v in dados["verba_gabinete"]]
        mensais += [{**base, "tipo": "salario", "mes": m, "valor": v, "disponivel": None} for m, v in salario]
        mensais.append({**base, "tipo": MARCA, "mes": 0, "valor": Decimal(0), "disponivel": None})
    if codigos and ok == 0:
        raise RuntimeError(f"Nenhuma página de deputado respondeu ({ano})")

    feitos = [c for c, d, _ in resultados if d is not None]
    with sessao() as s:
        s.execute(delete(Beneficio).where(Beneficio.casa == "camara", Beneficio.ano == ano, Beneficio.codigo_politico.in_(feitos)))
        s.execute(delete(RecursoMensal).where(RecursoMensal.casa == "camara", RecursoMensal.ano == ano, RecursoMensal.codigo_politico.in_(feitos)))
        if beneficios:
            s.execute(insert(Beneficio), beneficios)
        if mensais:
            s.execute(insert(RecursoMensal), mensais)
    logger.info("Câmara %s: recursos de %s deputados, %s benefícios, %s valores mensais", ano, ok, len(beneficios), len(mensais))
    return ok
