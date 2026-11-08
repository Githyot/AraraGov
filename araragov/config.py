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


# Saída com IP brasileiro para fontes públicas que recusam conexões de fora do país
# (alguns portais estaduais, tribunais de contas e a Receita não respondem aos
# servidores do GitHub, que ficam nos EUA). Formato: http://usuario:senha@host:porta
# ou socks5h://usuario:senha@host:porta. Vazio = sem saída brasileira.
# Ver docs/ip-brasileiro.md. Só é usada quando a conexão direta falha ou o servidor
# responde 403/451; nunca para driblar limite de pedidos (429).
PROXY_BR = os.environ.get("ARARAGOV_PROXY_BR", "").strip()

# Servidores que já se sabe que só respondem a IPs do Brasil: com PROXY_BR definido,
# vão direto por ele, sem gastar tempo com a tentativa direta. Mais hosts podem ser
# acrescentados por ARARAGOV_PROXY_HOSTS (separados por vírgula).
HOSTS_SO_BRASIL = frozenset(
    h.strip().lower()
    for h in (
        "arquivos.receitafederal.gov.br,dadosabertos.tce.pr.gov.br,"
        + os.environ.get("ARARAGOV_PROXY_HOSTS", "")
    ).split(",")
    if h.strip()
)
