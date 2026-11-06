"""Cliente HTTP com novas tentativas. Os coletores recebem um cliente, o que
permite testá-los com respostas gravadas (ver tests/conftest.py)."""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional, Set
from urllib.parse import urlsplit

import requests

from .config import HOSTS_SO_BRASIL, HTTP_TIMEOUT, PROXY_BR, USER_AGENT

logger = logging.getLogger(__name__)

# Respostas que costumam significar "seu IP não é do Brasil". Um 429 (pedidos demais)
# NÃO entra: trocar de IP para fugir de limite de pedidos é burlar o bloqueio.
STATUS_DE_BLOQUEIO_GEOGRAFICO = {403, 451}


def _sem_senha(proxy: str) -> str:
    """Endereço do proxy sem usuário e senha, para aparecer no log."""
    partes = urlsplit(proxy)
    return f"{partes.scheme}://{partes.hostname}:{partes.port}" if partes.hostname else "(proxy)"


class HttpClient:
    def __init__(
        self, tentativas: int = 6, espera_inicial: float = 2.0, proxy_br: Optional[str] = None
    ) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.tentativas = tentativas
        self.espera_inicial = espera_inicial
        # Servidores que não aceitaram conexão em nenhuma tentativa. Com o
        # servidor fora do ar, cada nova URL custaria vários minutos de
        # espera; melhor desistir logo e seguir para as outras fontes.
        self.fora_do_ar: Set[str] = set()
        # Saída com IP brasileiro (config.PROXY_BR). Os servidores em via_brasil passam
        # por ela; os outros só entram ali quando a conexão direta falha ou volta 403/451.
        self.proxy_br = PROXY_BR if proxy_br is None else proxy_br
        self.via_brasil: Set[str] = set(HOSTS_SO_BRASIL) if self.proxy_br else set()

    def _proxies(self, host: str) -> dict:
        if self.proxy_br and host in self.via_brasil:
            return {"proxies": {"http": self.proxy_br, "https": self.proxy_br}}
        return {}

    def _trocar_para_brasil(self, host: str, motivo: str) -> bool:
        """Passa o servidor para a saída brasileira, se houver uma e ele ainda não
        estiver nela. Devolve True quando vale tentar de novo na hora."""
        if not self.proxy_br or host in self.via_brasil:
            return False
        self.via_brasil.add(host)
        logger.warning(
            "%s em %s; tentando pela saída com IP brasileiro (%s)", motivo, host, _sem_senha(self.proxy_br)
        )
        return True

    def _get(self, url: str, params: Optional[Mapping[str, Any]], accept: str) -> requests.Response:
        host = (urlsplit(url).hostname or "").lower()
        if host in self.fora_do_ar:
            raise RuntimeError(f"{host} não respondeu antes nesta execução; pulando {url}")
        espera = self.espera_inicial
        so_falhas_de_conexao = True
        for tentativa in range(1, self.tentativas + 1):
            try:
                resp = self.session.get(
                    url, params=params, headers={"Accept": accept}, timeout=(20, HTTP_TIMEOUT),
                    **self._proxies(host),
                )
                so_falhas_de_conexao = False
                if resp.status_code in STATUS_DE_BLOQUEIO_GEOGRAFICO and self._trocar_para_brasil(
                    host, f"HTTP {resp.status_code}"
                ):
                    continue
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                    return resp
                logger.warning("HTTP %s em %s (tentativa %s)", resp.status_code, url, tentativa)
            except requests.ConnectionError as exc:
                logger.warning("Falha de conexão em %s (tentativa %s): %s", url, tentativa, exc)
                if self._trocar_para_brasil(host, "Sem conexão"):
                    continue
            except requests.Timeout:
                logger.warning("Tempo esgotado em %s (tentativa %s)", url, tentativa)
                if self._trocar_para_brasil(host, "Tempo esgotado"):
                    continue
            if tentativa < self.tentativas:
                time.sleep(espera)
                espera *= 2
        if so_falhas_de_conexao:
            self.fora_do_ar.add(host)
        raise RuntimeError(f"Não foi possível obter {url} após {self.tentativas} tentativas")

    def get_json(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self._get(url, params, "application/json").json()

    def get_bytes(self, url: str, params: Optional[Mapping[str, Any]] = None) -> bytes:
        return self._get(url, params, "*/*").content

    def baixar_arquivo(self, url: str, destino, pedaco: int = 1 << 20) -> None:
        """Baixa um arquivo grande direto para o disco, com novas tentativas.
        Se a conexão cair no meio e o servidor aceitar Range, continua de onde
        parou em vez de recomeçar."""
        host = (urlsplit(url).hostname or "").lower()
        espera = self.espera_inicial
        recebido = 0
        for tentativa in range(1, self.tentativas + 1):
            cabecalhos = {"Range": f"bytes={recebido}-"} if recebido else {}
            try:
                with self.session.get(
                    url, stream=True, timeout=(20, HTTP_TIMEOUT), headers=cabecalhos, **self._proxies(host)
                ) as resp:
                    if resp.status_code in STATUS_DE_BLOQUEIO_GEOGRAFICO and self._trocar_para_brasil(
                        host, f"HTTP {resp.status_code}"
                    ):
                        continue
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
                if recebido == 0 and self._trocar_para_brasil(host, "Sem conexão"):
                    continue
            if tentativa < self.tentativas:
                time.sleep(espera)
                espera *= 2
        raise RuntimeError(f"Não foi possível baixar {url} após {self.tentativas} tentativas")
