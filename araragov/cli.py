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
from .collectors import alba, alece, alesc, assembleias, beneficios, camara, camara_recursos, emendas, gabinete, historico, referencia, senado, tse
from .http import HttpClient

ALVOS = {
    # Primeiro, o que a coleta anterior já publicou e não muda (anos fechados).
    "historico": lambda c, a: historico.carregar(c),
    # Legislatura anterior primeiro: a coleta atual vem depois e atualiza
    # partido e situação de quem continua no mandato.
    "camara-deputados-anteriores": lambda c, a: camara.coletar_deputados(c, camara.legislatura_atual(c) - 1),
    "camara-deputados": lambda c, a: camara.coletar_deputados(c),
    "camara-votacoes": lambda c, a: camara.coletar_votacoes(c, a.ano, a.limite),
    "camara-despesas": lambda c, a: camara.coletar_despesas(c, a.ano, a.limite),
    "senado-senadores-anteriores": lambda c, a: senado.coletar_senadores_anteriores(c),
    "senado-senadores": lambda c, a: senado.coletar_senadores(c),
    "senado-votacoes": lambda c, a: senado.coletar_votacoes(c, a.ano, a.limite),
    "senado-despesas": lambda c, a: senado.coletar_despesas(c, a.ano, a.limite),
    "camara-gabinetes": lambda c, a: gabinete.coletar_camara(c),
    "camara-recursos": lambda c, a: camara_recursos.coletar_recursos(
        c, a.ano, a.limite, so_faltantes=a.ano < a.ano_final - 1
    ),
    "senado-gabinetes": lambda c, a: gabinete.coletar_senado(c),
    "senado-moradia": lambda c, a: beneficios.coletar_moradia_senado(c),
    "emendas": lambda c, a: emendas.coletar_emendas(c, a.ano, a.limite),
    # Estados: eleitos do TSE nos 27 estados. Onde a assembleia tem lista
    # própria (MG, SP), a coleta dela vem depois e substitui a do TSE; se a
    # assembleia estiver fora do ar, fica a lista do TSE.
    "estados-eleitos": lambda c, a: tse.coletar_eleitos(c),
    "almg-deputados": lambda c, a: assembleias.coletar_deputados_almg(c),
    "almg-despesas": lambda c, a: assembleias.coletar_despesas_almg(c, a.ano, a.limite),
    "alesp-deputados": lambda c, a: assembleias.coletar_deputados_alesp(c),
    "alesp-despesas": lambda c, a: assembleias.coletar_despesas_alesp(c, a.ano, a.limite),
    "alesc-deputados": lambda c, a: alesc.coletar_deputados(c),
    "alesc-despesas": lambda c, a: alesc.coletar_despesas(c, a.ano, a.limite),
    "alesc-gabinetes": lambda c, a: alesc.coletar_gabinetes(c),
    "alba-deputados": lambda c, a: alba.coletar_deputados(c),
    "alba-despesas": lambda c, a: alba.coletar_despesas(c, a.ano, a.limite),
    "alece-despesas": lambda c, a: alece.coletar_despesas(c, a.ano, a.limite),
    "ipca": lambda c, a: referencia.coletar_ipca(c),
    "subsidios": lambda c, a: referencia.carregar_subsidios(),
}


# Fontes com reserva: se falharem, o TSE já cobre o estado e a coleta segue
# sem marcar erro (o aviso aparece no log e no resumo).
COM_RESERVA = {"historico", "almg-deputados", "almg-despesas", "alesp-deputados", "alesp-despesas", "alesc-deputados", "alesc-despesas", "alesc-gabinetes", "alba-deputados", "alba-despesas", "alece-despesas"}


POR_ANO = {
    "camara-votacoes", "camara-despesas", "senado-votacoes", "senado-despesas",
    "almg-despesas", "alesp-despesas", "alesc-despesas", "alba-despesas", "alece-despesas", "emendas", "camara-recursos",
}


def _anos_do_alvo(alvo: str, anos: list[int]) -> list[int]:
    return anos if alvo in POR_ANO else anos[-1:]


def _anos(texto: str) -> list[int]:
    if "-" in texto:
        inicio, fim = (int(x) for x in texto.split("-", 1))
        return list(range(inicio, fim + 1))
    return [int(texto)]


def resumo() -> None:
    with db.sessao() as s:
        for modelo in (db.Politico, db.Votacao, db.Voto, db.Despesa, db.Assessor, db.Beneficio, db.RecursoMensal, db.Emenda, db.Favorecido, db.Ipca, db.Subsidio):
            total = s.execute(select(func.count()).select_from(modelo)).scalar_one()
            print(f"{modelo.__tablename__:10} {total:>10}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="araragov", description="Coleta de dados públicos do AraraGov")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="comando", required=True)
    col = sub.add_parser("coletar", help="baixa dados das fontes oficiais")
    col.add_argument("alvo", choices=[*ALVOS, "tudo"])
    col.add_argument(
        "--ano",
        type=_anos,
        default=[date.today().year],
        help="ano ou intervalo, ex.: 2025 ou 2023-2026 (padrão: ano atual)",
    )
    col.add_argument("--limite", type=int, help="processa só N itens (teste rápido)")
    sub.add_parser("resumo", help="mostra quantos registros há no banco")
    exp = sub.add_parser("exportar", help="gera a API estática (JSON) que o app lê")
    exp.add_argument("--saida", default="site", help="pasta de saída (padrão: site)")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.configurar()

    if args.comando == "resumo":
        resumo()
        return 0
    if args.comando == "exportar":
        from pathlib import Path

        from .exportar import exportar

        exportar(Path(args.saida))
        return 0

    client = HttpClient()
    alvos = list(ALVOS) if args.alvo == "tudo" else [args.alvo]
    falhas = []
    avisos = []
    anos = args.ano
    args.ano_final = anos[-1]
    for alvo in alvos:
        for ano in _anos_do_alvo(alvo, anos):
            args.ano = ano
            try:
                ALVOS[alvo](client, args)
            except Exception:
                logging.exception("Falha ao coletar %s (%s)", alvo, ano)
                (avisos if alvo in COM_RESERVA else falhas).append(f"{alvo} {ano}")
    resumo()
    if avisos:
        print("Indisponíveis (dados de reserva usados):", ", ".join(avisos), file=sys.stderr)
    if falhas:
        print("Falharam:", ", ".join(falhas), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
