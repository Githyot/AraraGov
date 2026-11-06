"""Reaproveita arquivos de anos fechados que já estão no ar (GitHub Pages).

Os tribunais de contas publicam um arquivo bruto por ano (o do TCE-SP tem
cerca de 2 GB). Depois que o ano fecha e as prefeituras terminam de enviar os
dados, o `.md` gerado dele não muda mais; baixá-lo de novo toda semana só gasta
tempo. Este módulo traz de volta o `.md` publicado na coleta anterior.

Um ano é considerado fechado a partir de abril do ano seguinte: até lá as
prefeituras ainda enviam os últimos meses e podem corrigir o que mandaram.

Só vale com `ARARAGOV_REAPROVEITAR=1` (a coleta semanal liga). Nos testes e nos
PRs fica desligado, para que os coletores rodem de verdade.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from . import md

logger = logging.getLogger(__name__)

PUBLICADO = "https://githyot.github.io/AraraGov"
MES_FECHAMENTO = 4


def ano_fechado(ano: int, hoje: date) -> bool:
    return ano < hoje.year - 1 or (ano == hoje.year - 1 and hoje.month >= MES_FECHAMENTO)


def _um(client, saida: Path, uf: str, cod: int, nome: str) -> bool:
    relativo = f"v1/municipios/{uf.lower()}/{cod}/{nome}"
    try:
        texto = client.get_bytes(f"{PUBLICADO}/{relativo}").decode("utf-8")
        md.ler(texto)
    except Exception:  # 404 (município sem arquivo) ou arquivo ilegível: fica de fora
        return False
    caminho = saida / relativo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return True


def reaproveitar(client, saida: Path, uf: str, codigos: Iterable[int], nome: str, trabalhadores: int = 8) -> int:
    """Copia `{uf}/{cod}/{nome}` já publicado para `saida`. Devolve quantos vieram."""
    codigos = list(codigos)
    with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
        n = sum(ex.map(lambda c: _um(client, saida, uf, c, nome), codigos))
    logger.info("%s %s: %s de %s municípios reaproveitados da publicação anterior", uf.upper(), nome, n, len(codigos))
    return n


def ano_ja_publicado(client, saida: Path, uf: str, ano: int, hoje: date, nome: str) -> int:
    """Se o ano está fechado e já foi publicado, copia os arquivos e devolve quantos.

    Devolve 0 quando o ano precisa ser coletado de novo (ano aberto, primeira
    publicação ou site fora do ar).
    """
    if os.environ.get("ARARAGOV_REAPROVEITAR") != "1" or not ano_fechado(ano, hoje):
        return 0
    from .eleitos import municipios_ibge

    codigos = sorted(cod for (u, _), (cod, _) in municipios_ibge().items() if u == uf.upper())
    return reaproveitar(client, saida, uf, codigos, nome.format(ano=ano))


# --- arquivo bruto sem mudança desde a última coleta -------------------------------------

# Um arquivo por fonte, para que coletas em paralelo (um job por tribunal) não se sobrescrevam.
ASSINATURAS = "v1/municipios/fontes-brutas"


def _arquivo(url: str) -> str:
    return f"{ASSINATURAS}/{hashlib.sha1(url.encode()).hexdigest()[:16]}.json"


def assinatura(client, url: str) -> Optional[Dict[str, str]]:
    """ETag, data e tamanho do arquivo no servidor (pedido HEAD, sem baixar)."""
    sessao = getattr(client, "session", None)
    if sessao is None:
        return None
    try:
        r = sessao.head(url, allow_redirects=True, timeout=30)
    except Exception:  # noqa: BLE001 - sem assinatura, baixa como sempre
        return None
    campos = {k: r.headers.get(k) for k in ("ETag", "Last-Modified", "Content-Length") if r.headers.get(k)}
    if not r.ok or not ({"ETag", "Last-Modified"} & set(campos)):
        return None
    return campos


def _assinatura_publicada(client, url: str) -> Optional[Dict[str, str]]:
    try:
        dados = json.loads(client.get_bytes(f"{PUBLICADO}/{_arquivo(url)}"))
    except Exception:  # noqa: BLE001 - primeira publicação
        return None
    return dados.get("assinatura") if dados.get("url") == url else None


def registrar(saida: Path, url: str, campos: Optional[Dict[str, str]]) -> None:
    """Guarda a assinatura do arquivo que gerou os .md desta coleta."""
    if not campos:
        return
    caminho = saida / _arquivo(url)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"url": url, "assinatura": campos}, ensure_ascii=False, indent=1), encoding="utf-8")


def sem_mudanca(client, saida: Path, uf: str, url: str, nome: str) -> Tuple[int, Optional[Dict[str, str]]]:
    """Se o arquivo bruto é o mesmo da coleta publicada, copia os .md publicados.

    Devolve (arquivos reaproveitados, assinatura atual). Zero quer dizer que
    é preciso baixar e processar de novo; registre a assinatura depois.
    """
    if os.environ.get("ARARAGOV_REAPROVEITAR") != "1":
        return 0, None
    atual = assinatura(client, url)
    if not atual or _assinatura_publicada(client, url) != atual:
        return 0, atual
    from .eleitos import municipios_ibge

    codigos = sorted(cod for (u, _), (cod, _) in municipios_ibge().items() if u == uf.upper())
    n = reaproveitar(client, saida, uf, codigos, nome)
    if n:
        registrar(saida, url, atual)
        logger.info("%s sem mudança desde a última coleta; %s arquivos reaproveitados", url, n)
    return n, atual
