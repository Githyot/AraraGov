"""Pagamentos dos municípios da Paraíba pelo TCE-PB (Sagres, dados consolidados).

O TCE-PB publica um zip por ano com todas as despesas de todos os municípios
(`download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-AAAA.zip`,
~190 MB, CSV em UTF-8 separado por `;`). Cada linha é um empenho com os
valores empenhado, liquidado e pago, o credor (CPF ou CNPJ), a função, a
subfunção e o elemento da despesa.

As linhas são traduzidas para os nomes de campo do TCE-SP e somadas por
`tcesp.agregar`, para sair no mesmo `{ano}-pagamentos.md`.

O CPF vem completo, preenchido com zeros à esquerda até 14 dígitos; ele é
reconhecido pelos dígitos verificadores e nunca é gravado (pessoas físicas
entram só no total).
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from . import publicados
from . import tcesp
from .eleitos import chave_nome, municipios_ibge
from .tcesp import PAGO, so_digitos

logger = logging.getLogger(__name__)

DESPESAS_URL = "https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-{ano}.zip"
FONTE = "https://dados-abertos.tce.pb.gov.br/dados-consolidados"


def cnpj_valido(d: str) -> bool:
    if len(d) != 14 or len(set(d)) == 1:
        return False

    def dv(base: str, pesos) -> str:
        r = sum(int(a) * b for a, b in zip(base, pesos)) % 11
        return "0" if r < 2 else str(11 - r)

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return dv(d[:12], p1) == d[12] and dv(d[:13], [6] + p1) == d[13]


def linhas(conteudo_zip: Path) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(conteudo_zip) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".csv"):
                with z.open(nome) as f:
                    yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""), delimiter=";")


def traduzir(rs: Iterable[Dict[str, str]], ibge: Dict[str, int]) -> Iterator[Dict[str, str]]:
    """Linha do Sagres -> linha no formato do TCE-SP (só o valor pago)."""
    for r in rs:
        cod = ibge.get(chave_nome(r.get("municipio") or ""))
        if not cod:
            continue
        doc = so_digitos(r.get("cpf_cnpj"))
        pj = cnpj_valido(doc)
        elemento = "".join(so_digitos(r.get(c)).zfill(n)[-n:] for c, n in (
            ("codigo_categoria_economica", 1), ("codigo_natureza", 1),
            ("codigo_modalidade_aplicacao", 2), ("codigo_elemento_despesa", 2)))
        yield {
            "tp_despesa": PAGO,
            "codigo_municipio_ibge": str(cod),
            "ds_municipio": r.get("municipio") or "",
            "vl_despesa": r.get("valor_pago") or "",
            "ds_elemento": f"{elemento} - {r.get('elemento_despesa') or ''}",
            "tp_identificador_despesa": "CNPJ" if pj else "CPF",
            # Pessoa física: só um marcador, nunca o CPF (tcesp guarda só um hash dele).
            "nr_identificador_despesa": doc if pj else (doc[-11:] if doc else ""),
            "ds_despesa": r.get("nome_credor") or "",
            "ds_funcao_governo": r.get("funcao") or "",
            "ds_subfuncao_governo": r.get("subfuncao") or "",
            "ds_orgao": r.get("descricao_unidade_gestora") or "",
            "nr_empenho": r.get("numero_empenho") or "",
            "ds_acao": r.get("acao") or "",
            "historico_despesa": r.get("historico") or "",
        }


def ibge_pb() -> Dict[str, int]:
    return {k: cod for (uf, k), (cod, _) in municipios_ibge().items() if uf == "PB"}


def gerar(client, saida: Path, anos: Iterable[int], limite_linhas: Optional[int] = None,
          hoje: Optional[date] = None, pasta_tmp: Optional[Path] = None) -> int:
    hoje = hoje or date.today()
    pasta_tmp = pasta_tmp or saida.parent / "tmp"
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    ibge = ibge_pb()
    nomes = {cod: nome for (uf, _), (cod, nome) in municipios_ibge().items() if uf == "PB"}
    total = 0
    for ano in sorted(anos):
        reaproveitados = publicados.ano_ja_publicado(client, saida, "PB", ano, hoje, "{ano}-pagamentos.md")
        if reaproveitados:
            total += reaproveitados
            continue
        url = DESPESAS_URL.format(ano=ano)
        reaproveitados, assinatura = publicados.sem_mudanca(client, saida, "PB", url, f"{ano}-pagamentos.md")
        if reaproveitados:
            total += reaproveitados
            continue
        arquivo = pasta_tmp / f"tcepb-despesas-{ano}.zip"
        tcesp.baixar(client, url, arquivo)
        municipios = tcesp.agregar(traduzir(linhas(arquivo), ibge), limite_linhas)
        for cod, m in municipios.items():
            m.nome = nomes.get(cod, m.nome)
            caminho = saida / "v1" / "municipios" / "pb" / str(cod) / f"{ano}-pagamentos.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(tcesp.documento(cod, ano, m, hoje, tcesp._governo(saida, cod, ano, "PB"),
                                               uf="PB", fonte=FONTE, tribunal="TCE-PB (Sagres)"), encoding="utf-8")
        arquivo.unlink(missing_ok=True)
        publicados.registrar(saida, url, assinatura)
        logger.info("TCE-PB %s: %s municípios", ano, len(municipios))
        total += len(municipios)
    return total
