"""Configuração por variáveis de ambiente."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DB_PATH = Path("dados") / "araragov.db"


def database_url() -> str:
    """URL do banco. Padrão: SQLite local em ./dados/araragov.db.

    Em produção, use Postgres: DATABASE_URL=postgresql+psycopg://user:senha@host/araragov
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH}"


USER_AGENT = "AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
HTTP_TIMEOUT = float(os.environ.get("ARARAGOV_HTTP_TIMEOUT", "120"))
