"""Linha de comando.

    araragov coletar tudo --ano 2025
    araragov coletar camara-votacoes --ano 2025 --limite 20
    araragov resumo
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from sqlalchemy import func, select

from . import db
from .collectors import camara, referencia, senado
from .http import HttpClient

ALVOS = {
    "camara-deputados": lambda c, a: camara.coletar_deputados(c),
    "camara-votacoes": lambda c, a: camara.coletar_votacoes(c, a.ano, a.limite),
    "camara-despesas": lambda c, a: camara.coletar_despesas(c, a.ano, a.limite),
    "senado-senadores": lambda c, a: senado.coletar_senadores(c),
    "senado-votacoes": lambda c, a: senado.coletar_votacoes(c, a.ano, a.limite),
    "senado-despesas": lambda c, a: senado.coletar_despesas(c, a.ano, a.limite),
    "ipca": lambda c, a: referencia.coletar_ipca(c),
    "subsidios": lambda c, a: referencia.carregar_subsidios(),
}


def resumo() -> None:
    with db.sessao() as s:
        for modelo in (db.Politico, db.Votacao, db.Voto, db.Despesa, db.Ipca, db.Subsidio):
            total = s.execute(select(func.count()).select_from(modelo)).scalar_one()
            print(f"{modelo.__tablename__:10} {total:>10}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="araragov", description="Coleta de dados públicos do AraraGov")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="comando", required=True)
    col = sub.add_parser("coletar", help="baixa dados das fontes oficiais")
    col.add_argument("alvo", choices=[*ALVOS, "tudo"])
    col.add_argument("--ano", type=int, default=date.today().year)
    col.add_argument("--limite", type=int, help="processa só N itens (teste rápido)")
    sub.add_parser("resumo", help="mostra quantos registros há no banco")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.configurar()

    if args.comando == "resumo":
        resumo()
        return 0

    client = HttpClient()
    alvos = list(ALVOS) if args.alvo == "tudo" else [args.alvo]
    falhas = []
    for alvo in alvos:
        try:
            ALVOS[alvo](client, args)
        except Exception:
            logging.exception("Falha ao coletar %s", alvo)
            falhas.append(alvo)
    resumo()
    if falhas:
        print("Falharam:", ", ".join(falhas), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
