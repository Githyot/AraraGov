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
from .collectors import alba, alece, alepa, alero, alesc, assembleias, beneficios, camara, camara_recursos, emendas, gabinete, historico, ocorrencias, referencia, senado, tse
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
    "alece-deputados": lambda c, a: alece.coletar_deputados(c),
    "alece-despesas": lambda c, a: alece.coletar_despesas(c, a.ano, a.limite),
    "alepa-gabinetes": lambda c, a: alepa.coletar_gabinetes(c),
    "alero-gabinetes": lambda c, a: alero.coletar_gabinetes(c),
    "ipca": lambda c, a: referencia.coletar_ipca(c),
    "subsidios": lambda c, a: referencia.carregar_subsidios(),
    # Por último: precisa de todos os políticos já gravados para cruzar.
    "ocorrencias": lambda c, a: ocorrencias.coletar(c),
}


# Fontes com reserva: se falharem, o TSE já cobre o estado e a coleta segue
# sem marcar erro (o aviso aparece no log e no resumo).
COM_RESERVA = {"historico", "ocorrencias", "almg-deputados", "almg-despesas", "alesp-deputados", "alesp-despesas", "alesc-deputados", "alesc-despesas", "alesc-gabinetes", "alba-deputados", "alba-despesas", "alece-deputados", "alece-despesas", "alepa-gabinetes", "alero-gabinetes"}


POR_ANO = {
    "camara-votacoes", "camara-despesas", "senado-votacoes", "senado-despesas",
    "almg-despesas", "alesp-despesas", "alesc-despesas", "alba-despesas", "alece-despesas", "emendas", "camara-recursos",
}


def _anos_do_alvo(alvo: str, anos: list[int]) -> list[int]:
    return anos if alvo in POR_ANO else anos[-1:]


def _anos(texto: str) -> list[int]:
    if "," in texto:
        return sorted({a for parte in texto.split(",") if parte.strip() for a in _anos(parte.strip())})
    if "-" in texto:
        inicio, fim = (int(x) for x in texto.split("-", 1))
        return list(range(inicio, fim + 1))
    return [int(texto)]


def resumo() -> None:
    with db.sessao() as s:
        for modelo in (db.Politico, db.Votacao, db.Voto, db.Despesa, db.Assessor, db.Beneficio, db.RecursoMensal, db.Emenda, db.Favorecido, db.Ocorrencia, db.Ipca, db.Subsidio):
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
    mun = sub.add_parser("municipios", help="gera os arquivos .md dos municípios (prefeitos e vereadores, TSE)")
    mun.add_argument("--saida", default="site", help="pasta de saída (padrão: site)")
    mun.add_argument("--anos", default="2016,2020,2024", help="eleições municipais, ex.: 2024 ou 2016,2020,2024")
    mun.add_argument("--ufs", default="", help="só estes estados, ex.: PR,SC (padrão: todos)")
    mun.add_argument("--financas", type=_anos, default=[], help="anos de arrecadação e gastos (Siconfi), ex.: 2019-2025")
    mun.add_argument("--limite-siconfi", type=int, help="máximo de pares município-ano buscados no Siconfi nesta execução")
    mun.add_argument("--mensal", type=_anos, default=[], help="anos de arrecadação e gastos mês a mês (Siconfi, MSC)")
    mun.add_argument("--limite-msc", type=int, help="máximo de pedidos município-mês à MSC nesta execução")
    mun.add_argument("--sem-eleitos", action="store_true", help="não gera os resumos com prefeitos e vereadores")
    cus = sub.add_parser("custos", help="gera os custos de referência por estado (.md)")
    cus.add_argument("--saida", default="site")
    cus.add_argument("--anos", type=_anos, default=_anos(f"2016-{date.today().year}"))
    cus.add_argument("--ufs", default="", help="ex.: PR,SC (padrão: todos)")
    tsp = sub.add_parser("tce-sp", help="pagamentos dos municípios de SP pelo TCE-SP (.md)")
    tsp.add_argument("--saida", default="site")
    tsp.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    tsp.add_argument("--limite-linhas", type=int, help="lê só N linhas do arquivo (teste)")
    tce = sub.add_parser("tce-ce", help="pagamentos dos municípios do CE pelo TCE-CE (.md)")
    tce.add_argument("--saida", default="site")
    tce.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    tce.add_argument("--limite-municipios", type=int, help="só os N primeiros municípios (teste)")
    tce.add_argument("--meses", type=int, help="só os N primeiros meses de cada ano (teste)")
    tpb = sub.add_parser("tce-pb", help="pagamentos dos municípios da PB pelo TCE-PB (.md)")
    tpb.add_argument("--saida", default="site")
    tpb.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    tpb.add_argument("--limite-linhas", type=int, help="lê só N linhas do arquivo (teste)")
    tpe = sub.add_parser("tce-pe", help="pagamentos dos municípios de PE pelo TCE-PE (.md)")
    tpe.add_argument("--saida", default="site")
    tpe.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    tpe.add_argument("--limite-municipios", type=int, help="só os N primeiros municípios (teste)")
    fdc = sub.add_parser("fiorilli-descobrir", help="procura portais Fiorilli das prefeituras (lista .csv)")
    fdc.add_argument("--saida", default="araragov/referencia/fiorilli.csv")
    fdc.add_argument("--ufs", default="", help="ex.: GO,MG (padrão: todos)")
    fio = sub.add_parser("fiorilli", help="pagamentos das prefeituras com portal Fiorilli (.md)")
    fio.add_argument("--saida", default="site")
    fio.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    fio.add_argument("--limite-municipios", type=int, help="só as N primeiras prefeituras (teste)")
    agl = sub.add_parser("agili", help="pagamentos das prefeituras com portal Agili/IPM, quase todas do MT (.md)")
    agl.add_argument("--saida", default="site")
    agl.add_argument("--anos", type=_anos, default=[date.today().year - 1])
    agl.add_argument("--limite-municipios", type=int, help="só as N primeiras prefeituras (teste)")
    agl.add_argument("--limite-linhas", type=int, help="lê só N empenhos de cada prefeitura (teste)")
    trj = sub.add_parser("tce-rj", help="contratos dos municípios do RJ pelo TCE-RJ (.md)")
    trj.add_argument("--saida", default="site")
    trj.add_argument("--anos", type=_anos, default=[date.today().year - 1, date.today().year])
    trj.add_argument("--limite-municipios", type=int, help="só os N primeiros municípios (teste)")
    frn = sub.add_parser("fornecedores", help="fornecedores dos municípios com sanções (CEIS/CNEP) e campanhas (TSE)")
    frn.add_argument("--saida", default="site")
    frn.add_argument("--ufs", default="SP", help="estados com contratos coletados, ex.: SP,SC ou todos")
    frn.add_argument("--eleicoes", type=_anos, default=[2016, 2020, 2024], help="eleições municipais, ex.: 2020,2024")
    loc = sub.add_parser("coleta-local", help="coleta mensal no computador do mantenedor (SINAPI e sócios da Receita)")
    loc.add_argument("--saida", default="dados/locais", help="pasta dos arquivos (padrão: dados/locais)")
    loc.add_argument("--mes", default="", help="mês do SINAPI, AAAA-MM (padrão: dois meses atrás)")
    loc.add_argument("--cnpjs", default="", help="lista de CNPJs dos fornecedores (arquivo ou URL)")
    loc.add_argument("--so", choices=["sinapi", "socios"], help="só uma das fontes")
    loc.add_argument("--cache", default="", help="pasta para os zips da Receita (padrão: ~/.cache/araragov)")
    pnc = sub.add_parser("pncp", help="contratos dos municípios (fora de SP) pelo PNCP (.md)")
    pnc.add_argument("--saida", default="site")
    pnc.add_argument("--anos", type=_anos, default=[date.today().year - 1, date.today().year])
    pnc.add_argument("--dias", type=int, help="só os primeiros N dias de cada ano (teste)")
    pnc.add_argument("--limite-itens", type=int, default=3000, help="máximo de compras com itens consultados")
    pnc.add_argument("--parte", help="i/n: baixa só a parte i de n das semanas e grava em --partes (sem .md)")
    pnc.add_argument("--juntar", action="store_true", help="junta as partes de --partes e escreve os .md")
    pnc.add_argument("--partes", default="pncp-partes", help="pasta das partes (padrão: pncp-partes)")
    eme = sub.add_parser("emendas-municipios", help="emendas federais recebidas em cada município (.md)")
    eme.add_argument("--saida", default="site")
    eme.add_argument("--anos", type=_anos, default=_anos(f"2019-{date.today().year}"), help="anos do pagamento")
    eme.add_argument("--ufs", default="", help="ex.: AC,SP (padrão: todos)")
    son = sub.add_parser("sinapi-sondar", help="mostra o formato do pacote mensal do SINAPI")
    son.add_argument("--mes", default="", help="AAAA-MM (padrão: dois meses atrás)")
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

    if args.comando == "custos":
        from pathlib import Path

        from .collectors.tse import UFS
        from .municipios import referencias

        ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()] or list(UFS) + ["DF"]
        referencias.gerar(HttpClient(), Path(args.saida), sorted(set(ufs)), args.anos)
        return 0

    if args.comando == "tce-sp":
        from pathlib import Path

        from .municipios import contratos, tcesp

        client = HttpClient()
        n_contratos = contratos.gerar(client, Path(args.saida), args.anos)
        n_pagamentos = tcesp.gerar(client, Path(args.saida), args.anos, args.limite_linhas)
        return 0 if n_contratos and n_pagamentos else 1

    if args.comando == "tce-ce":
        from pathlib import Path

        from .municipios import tcece

        n = tcece.gerar(HttpClient(), Path(args.saida), args.anos, limite_municipios=args.limite_municipios,
                        meses=args.meses, novo_client=HttpClient)
        return 0 if n else 1

    if args.comando == "tce-pb":
        from pathlib import Path

        from .municipios import tcepb

        return 0 if tcepb.gerar(HttpClient(), Path(args.saida), args.anos, args.limite_linhas) else 1

    if args.comando == "tce-pe":
        from pathlib import Path

        from .municipios import tcepe

        return 0 if tcepe.gerar(HttpClient(), Path(args.saida), args.anos, args.limite_municipios) else 1

    if args.comando == "fiorilli-descobrir":
        from pathlib import Path

        from .municipios import fiorilli

        achados = fiorilli.descobrir([u for u in args.ufs.split(",") if u] or None)
        Path(args.saida).write_text(fiorilli.escrever_lista(achados), encoding="utf-8")
        return 0

    if args.comando == "fiorilli":
        from pathlib import Path

        from .municipios import fiorilli

        return 0 if fiorilli.gerar(HttpClient(), Path(args.saida), args.anos, args.limite_municipios) else 1

    if args.comando == "agili":
        from pathlib import Path

        from .municipios import agili

        n = agili.gerar(HttpClient(), Path(args.saida), args.anos, args.limite_municipios, args.limite_linhas)
        return 0 if n else 1

    if args.comando == "tce-rj":
        from pathlib import Path

        from .municipios import tcerj

        return 0 if tcerj.gerar(HttpClient(), Path(args.saida), args.anos, limite_municipios=args.limite_municipios) else 1

    if args.comando == "fornecedores":
        from pathlib import Path

        from .municipios import fornecedores

        ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()]
        if ufs == ["TODOS"]:
            from .collectors.tse import UFS

            ufs = sorted(set(UFS) | {"DF"})
        return 0 if fornecedores.gerar(HttpClient(), Path(args.saida), ufs, args.eleicoes) else 1

    if args.comando == "coleta-local":
        from pathlib import Path

        from .municipios import locais

        saida = Path(args.saida)
        if args.mes:
            ano, mes = (int(x) for x in args.mes.split("-"))
        else:
            hoje = date.today()
            ano, mes = (hoje.year, hoje.month - 2) if hoje.month > 2 else (hoje.year - 1, hoje.month + 10)
        ok = True
        if args.so in (None, "sinapi"):
            try:
                arq = locais.coletar_sinapi(ano, mes, saida)
                locais.candidatos_sinapi(arq, saida / "sinapi" / "candidatos-catalogo.csv")
            except Exception as e:  # noqa: BLE001
                logging.error("SINAPI: %s", e)
                ok = False
        if args.so in (None, "socios"):
            sessao = locais._sessao()
            padrao = saida / "cnpjs-fornecedores.txt"
            origem = args.cnpjs or (str(padrao) if padrao.exists() else locais.CNPJS_URL)
            cnpjs = locais.ler_cnpjs(origem, sessao)
            logging.info("Sócios: %s empresas na lista (%s)", len(cnpjs), origem)
            cache = Path(args.cache) if args.cache else Path.home() / ".cache" / "araragov"
            try:
                locais.coletar_socios(saida, cnpjs, cache, sessao)
            except Exception as e:  # noqa: BLE001
                logging.error("Sócios: %s", e)
                ok = False
        return 0 if ok else 1

    if args.comando == "pncp":
        from pathlib import Path

        from .municipios import pncp

        if args.parte:
            i, n = (int(x) for x in args.parte.split("/"))
            pncp.baixar_parte(HttpClient(), Path(args.partes), args.anos, i, n, dias=args.dias)
            return 0
        if args.juntar:
            return 0 if pncp.juntar(HttpClient(), Path(args.partes), Path(args.saida), args.anos,
                                    limite_itens=args.limite_itens) else 1
        return 0 if pncp.gerar(HttpClient(), Path(args.saida), args.anos, dias=args.dias,
                               limite_itens=args.limite_itens) else 1

    if args.comando == "emendas-municipios":
        from pathlib import Path

        from .municipios import emendas as emendas_mun

        ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()] or None
        return 0 if emendas_mun.gerar(HttpClient(), Path(args.saida), args.anos, ufs) else 1

    if args.comando == "sinapi-sondar":
        from .municipios import sinapi

        if args.mes:
            ano, mes = (int(x) for x in args.mes.split("-"))
        else:
            hoje = date.today()
            ano, mes = (hoje.year, hoje.month - 2) if hoje.month > 2 else (hoje.year - 1, hoje.month + 10)
        for parte in sinapi.sondar(sinapi.baixar(HttpClient(), ano, mes)):
            print(f"== {parte['arquivo']} | {parte['aba']} | {parte['dimensao']} linhas")
            for linha in parte["amostra"]:
                print("   ", linha)
        return 0

    if args.comando == "municipios":
        from pathlib import Path

        from .collectors.tse import UFS
        from .municipios import eleitos, financas, mensal

        ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()] or list(UFS)
        ok = True
        if not args.sem_eleitos:
            anos = [int(a) for a in args.anos.split(",") if a.strip()]
            ok = eleitos.gerar(HttpClient(), Path(args.saida), anos=anos, ufs=ufs) > 0
        if args.financas:
            r = financas.gerar(HttpClient, Path(args.saida), anos=args.financas, ufs=ufs,
                               limite_siconfi=args.limite_siconfi)
            ok = ok and (r["siconfi"] + r["reaproveitados"]) > 0
        if args.mensal:
            r = mensal.gerar(HttpClient, Path(args.saida), anos=args.mensal, ufs=ufs, limite=args.limite_msc)
            ok = ok and r["arquivos"] > 0
        return 0 if ok else 1

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
