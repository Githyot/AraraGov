"""Pagamentos dos municípios de Pernambuco pelo TCE-PE (Dados Abertos / Sagres).

O TCE-PE tem uma API de dados abertos que devolve JSON (em latin-1):

- `UnidadesJurisdicionadas!json` lista prefeituras, câmaras e fundos, com o
  código do município no tribunal (`CODIGOMUNICIPIO`, ex.: "P120" = Recife);
- `DespesasMunicipais!json?ANOREFERENCIA=AAAA&CODIGO_MUNICIPIO=P120` devolve
  os empenhos do ano de todas as unidades do município, com credor (CPF ou
  CNPJ), função, subfunção, elemento, histórico e os valores empenhado,
  liquidado e pago.

Cada resposta tem no máximo 100 mil linhas. Um município que passa disso é
pedido mês a mês (`MESREFERENCIA`).

As linhas são traduzidas para os campos do TCE-SP e somadas por
`tcesp.agregar`, para sair no mesmo `pe/{ibge}/{ano}-pagamentos.md`. CPF nunca
é gravado: pessoas físicas entram só no total.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import publicados
from . import tcesp
from .eleitos import chave_nome, municipios_ibge
from .tcepb import cnpj_valido
from .tcesp import PAGO, so_digitos

logger = logging.getLogger(__name__)

API = "https://sistemas.tce.pe.gov.br/DadosAbertos"
DESPESAS = API + "/DespesasMunicipais!json"
UNIDADES = API + "/UnidadesJurisdicionadas!json"
FONTE = "https://sistemas.tce.pe.gov.br/DadosAbertos/"
TRIBUNAL = "TCE-PE"

# O TCE-PE manda o elemento só por extenso; os códigos abaixo reproduzem os
# prefixos que tcesp usa para separar pessoal/dívida (31, 32, 46) e obras (449051).
_CATEGORIA = {"DESPESA CORRENTE": "3", "DESPESA DE CAPITAL": "4"}
_GRUPO = {"PESSOAL E ENCARGOS SOCIAIS": "1", "JUROS E ENCARGOS DA DIVIDA": "2", "OUTRAS DESPESAS CORRENTES": "3",
          "INVESTIMENTOS": "4", "INVERSOES FINANCEIRAS": "5", "AMORTIZACAO DA DIVIDA": "6"}


# Nomes que o TCE-PE escreve diferente do IBGE.
_NOMES_TCE = {"BELEM DE SAO FRANCISCO": "BELEM DO SAO FRANCISCO"}


class LimiteAtingido(Exception):
    pass


def _ler(client, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    bruto = client.get_bytes(url, params)
    return json.loads(bruto.decode("latin-1")).get("resposta") or {}


def codigos(client) -> Dict[str, Tuple[int, str]]:
    """Código do município no TCE-PE ("P120") -> (código IBGE, nome oficial)."""
    ibge = {k: v for (uf, k), v in municipios_ibge().items() if uf == "PE"}
    saida: Dict[str, Tuple[int, str]] = {}
    vistos = set()
    for u in _ler(client, UNIDADES, {}).get("conteudo") or []:
        cod = (u.get("CODIGOMUNICIPIO") or "").strip()
        if (u.get("UNIDADEFEDERATIVA") or "").strip() != "PE" or not cod or cod in vistos:
            continue
        vistos.add(cod)
        nome = chave_nome(u.get("MUNICIPIO") or "")
        achado = ibge.get(_NOMES_TCE.get(nome, nome))
        if achado:
            saida[cod] = achado
        else:
            logger.info("TCE-PE: município %r (%s) sem código IBGE", u.get("MUNICIPIO"), cod)
    return saida


def _pedido(client, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    r = _ler(client, DESPESAS, params)
    if (r.get("status") or "").upper() != "OK":
        return []
    linhas = r.get("conteudo") or []
    if len(linhas) >= int(r.get("limiteResultado") or 100000):
        raise LimiteAtingido()
    return linhas


def despesas(client, cod_tce: str, ano: int) -> Iterator[Dict[str, Any]]:
    params = {"ANOREFERENCIA": ano, "CODIGO_MUNICIPIO": cod_tce}
    try:
        yield from _pedido(client, params)
        return
    except LimiteAtingido:
        logger.info("TCE-PE %s %s: mais de 100 mil linhas, pedindo mês a mês", cod_tce, ano)
    for mes in range(1, 13):
        try:
            yield from _pedido(client, {**params, "MESREFERENCIA": mes})
        except LimiteAtingido:
            raise RuntimeError(f"TCE-PE {cod_tce} {ano}/{mes}: mais de 100 mil linhas num mês só")


def _codigo_elemento(r: Dict[str, Any]) -> str:
    cat = _CATEGORIA.get(chave_nome(r.get("CATEGORIA") or ""), "0")
    grupo = _GRUPO.get(chave_nome(r.get("NATUREZA") or ""), "0")
    elemento = "51" if chave_nome(r.get("ELEMENTODESPESA") or "").startswith("OBRAS E INSTALAC") else "00"
    return f"{cat}{grupo}90{elemento}"


def _brl(v: Any) -> str:
    """'4760.01' (ponto decimal) -> '4760,01', que é o que tcesp.valor lê."""
    return str(v or "0").strip().replace(".", ",")


def traduzir(rs: Iterable[Dict[str, Any]], cod: int, nome: str) -> Iterator[Dict[str, str]]:
    for r in rs:
        doc = so_digitos(r.get("CPF_CNPJ"))
        # TIPOCREDOR 1 é pessoa física e 3 é servidor (folha); o CPF vem com zeros à esquerda.
        pj = cnpj_valido(doc) and (r.get("TIPOCREDOR") or "").strip() not in ("1", "3")
        yield {
            "tp_despesa": PAGO,
            "codigo_municipio_ibge": str(cod),
            "ds_municipio": nome,
            "vl_despesa": _brl(r.get("VALORPAGO")),
            "ds_elemento": f"{_codigo_elemento(r)} - {r.get('ELEMENTODESPESA') or ''}",
            "tp_identificador_despesa": "CNPJ" if pj else "CPF",
            # Pessoa física: só um marcador; tcesp guarda só um hash dele.
            "nr_identificador_despesa": doc if pj else doc[-11:],
            "ds_despesa": r.get("FORNECEDOR") or "",
            "ds_funcao_governo": (r.get("FUNCAO") or "").strip(),
            "ds_subfuncao_governo": (r.get("SUBFUNCAO") or "").strip(),
            "ds_orgao": (r.get("NOMEUNIDADEGESTORA") or "").strip(),
            "nr_empenho": (r.get("NUMEROEMPENHO") or "").strip() + "/" + (r.get("ID_EMPENHO") or "").strip(),
            "ds_acao": r.get("ACAO") or "",
            "historico_despesa": r.get("HISTORICO") or "",
        }


def _um(client, saida: Path, cod_tce: str, cod: int, nome: str, ano: int, hoje: date) -> bool:
    try:
        municipios = tcesp.agregar(traduzir(despesas(client, cod_tce, ano), cod, nome))
    except Exception as exc:  # noqa: BLE001 - um município com erro não para os outros
        logger.warning("TCE-PE %s (%s) %s: %s", nome, cod_tce, ano, exc)
        return False
    m = municipios.get(cod)
    if not m:
        return False
    m.nome = nome
    caminho = saida / "v1" / "municipios" / "pe" / str(cod) / f"{ano}-pagamentos.md"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(tcesp.documento(cod, ano, m, hoje, tcesp._governo(saida, cod, ano, "PE"), uf="PE",
                                       fonte=FONTE, tribunal=TRIBUNAL), encoding="utf-8")
    return True


def gerar(client, saida: Path, anos: Iterable[int], limite_municipios: Optional[int] = None,
          hoje: Optional[date] = None, trabalhadores: int = 3) -> int:
    """Um pedido por município e ano, três ao mesmo tempo (o de Recife tem ~70 MB)."""
    hoje = hoje or date.today()
    lista = sorted(codigos(client).items())[:limite_municipios]
    logger.info("TCE-PE: %s municípios", len(lista))
    total = 0
    for ano in sorted(anos):
        reaproveitados = publicados.ano_ja_publicado(client, saida, "PE", ano, hoje, "{ano}-pagamentos.md")
        if reaproveitados:
            total += reaproveitados
            continue
        with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
            feitos = sum(ex.map(lambda p: _um(client, saida, p[0], p[1][0], p[1][1], ano, hoje), lista))
        logger.info("TCE-PE %s: %s de %s municípios", ano, feitos, len(lista))
        total += feitos
    return total
