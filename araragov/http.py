"""Cliente HTTP com novas tentativas. Os coletores recebem um cliente, o que
permite testá-los com respostas gravadas (ver tests/conftest.py)."""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional

import requests

from .config import HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, tentativas: int = 6, espera_inicial: float = 2.0) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.tentativas = tentativas
        self.espera_inicial = espera_inicial

    def _get(self, url: str, params: Optional[Mapping[str, Any]], accept: str) -> requests.Response:
        espera = self.espera_inicial
        for tentativa in range(1, self.tentativas + 1):
            try:
                resp = self.session.get(
                    url, params=params, headers={"Accept": accept}, timeout=HTTP_TIMEOUT
                )
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
        raise RuntimeError(f"Não foi possível obter {url} após {self.tentativas} tentativas")

    def get_json(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self._get(url, params, "application/json").json()

    def get_bytes(self, url: str, params: Optional[Mapping[str, Any]] = None) -> bytes:
        return self._get(url, params, "*/*").content
