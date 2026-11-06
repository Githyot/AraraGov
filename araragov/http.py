"""Cliente HTTP com novas tentativas. Os coletores recebem um cliente, o que
permite testá-los com respostas gravadas (ver tests/conftest.py)."""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional, Set
from urllib.parse import urlsplit

import requests

from .config import HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, tentativas: int = 6, espera_inicial: float = 2.0) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.tentativas = tentativas
        self.espera_inicial = espera_inicial
        # Servidores que não aceitaram conexão em nenhuma tentativa. Com o
        # servidor fora do ar, cada nova URL custaria vários minutos de
        # espera; melhor desistir logo e seguir para as outras fontes.
        self.fora_do_ar: Set[str] = set()

    def _get(self, url: str, params: Optional[Mapping[str, Any]], accept: str) -> requests.Response:
        return self._pedir("GET", url, params, {"Accept": accept})

    def _pedir(self, metodo: str, url: str, params: Optional[Mapping[str, Any]], cabecalhos: Mapping[str, str],
               corpo: Any = None) -> requests.Response:
        host = urlsplit(url).netloc
        if host in self.fora_do_ar:
            raise RuntimeError(f"{host} não respondeu antes nesta execução; pulando {url}")
        espera = self.espera_inicial
        so_falhas_de_conexao = True
        for tentativa in range(1, self.tentativas + 1):
            try:
                resp = self.session.request(
                    metodo, url, params=params, headers=dict(cabecalhos), json=corpo, timeout=(20, HTTP_TIMEOUT)
                )
                so_falhas_de_conexao = False
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                    return resp
                logger.warning("HTTP %s em %s (tentativa %s)", resp.status_code, url, tentativa)
            except requests.ConnectionError as exc:
                logger.warning("Falha de conexão em %s (tentativa %s): %s", url, tentativa, exc)
            except requests.Timeout:
                logger.warning("Tempo esgotado em %s (tentativa %s)", url, tentativa)
            if tentativa < self.tentativas:
                time.sleep(espera)
                espera *= 2
        if so_falhas_de_conexao:
            self.fora_do_ar.add(host)
        raise RuntimeError(f"Não foi possível obter {url} após {self.tentativas} tentativas")

    def get_json(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self._get(url, params, "application/json").json()

    def pedir_json(self, metodo: str, url: str, corpo: Any = None,
                   cabecalhos: Optional[Mapping[str, str]] = None) -> Any:
        """GET ou POST com corpo JSON e cabeçalhos extras (APIs de portais de transparência)."""
        return self._pedir(metodo, url, None, {"Accept": "application/json", **(cabecalhos or {})}, corpo).json()

    def get_bytes(self, url: str, params: Optional[Mapping[str, Any]] = None) -> bytes:
        return self._get(url, params, "*/*").content

    def baixar_arquivo(self, url: str, destino, pedaco: int = 1 << 20) -> None:
        """Baixa um arquivo grande direto para o disco, com novas tentativas.
        Se a conexão cair no meio e o servidor aceitar Range, continua de onde
        parou em vez de recomeçar."""
        espera = self.espera_inicial
        recebido = 0
        for tentativa in range(1, self.tentativas + 1):
            cabecalhos = {"Range": f"bytes={recebido}-"} if recebido else {}
            try:
                with self.session.get(url, stream=True, timeout=(20, HTTP_TIMEOUT), headers=cabecalhos) as resp:
                    if resp.status_code < 500 and resp.status_code != 429:
                        resp.raise_for_status()
                        continuar = recebido > 0 and resp.status_code == 206
                        if not continuar:
                            recebido = 0
                        with open(destino, "ab" if continuar else "wb") as f:
                            for parte in resp.iter_content(pedaco):
                                f.write(parte)
                                recebido += len(parte)
                        return
                    logger.warning("HTTP %s em %s (tentativa %s)", resp.status_code, url, tentativa)
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as exc:
                logger.warning("Falha ao baixar %s (tentativa %s, %s bytes até aqui): %s", url, tentativa, recebido, exc)
            if tentativa < self.tentativas:
                time.sleep(espera)
                espera *= 2
        raise RuntimeError(f"Não foi possível baixar {url} após {self.tentativas} tentativas")
