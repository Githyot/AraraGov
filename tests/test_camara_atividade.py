import json
from datetime import date

from araragov import db
from araragov.collectors import camara_atividade as ca
from araragov.collectors.camara import API, ARQUIVOS
from araragov.exportar import exportar


def _csv(cabecalho, linhas):
    texto = ";".join(f'"{c}"' for c in cabecalho) + "\n"
    for l in linhas:
        texto += ";".join(f'"{v}"' for v in l) + "\n"
    return ("﻿" + texto).encode("utf-8")


PROP_CAB = ["id", "siglaTipo", "numero", "ano", "ementa", "dataApresentacao", "uriPropPrincipal", "ultimoStatus_descricaoSituacao"]
URI = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/"
PROPOSICOES = [
    ["1", "PL", "10", "2026", "Cria o programa A.", "2026-03-01T10:00", "", "Aguardando Parecer"],
    ["2", "PEC", "3", "2026", "Altera a Constituição.", "2026-04-01T10:00", "", ""],
    ["3", "PRL", "1", "2026", "Parecer do Relator, Dep. Fulano (MISSÃO-SP), pela aprovação.", "2026-05-01T10:00", URI + "1", ""],
    ["4", "PRL", "2", "2026", "Parecer do Relator, Dep. Fulano (MISSÃO-SP), pela rejeição.", "2026-06-01T10:00", URI + "1", ""],
    ["5", "PRL", "3", "2026", "Parecer do Relator, Dep. Fulano, pela aprovação.", "2026-06-02T10:00", URI + "9", ""],
    ["6", "PRL", "4", "2026", "Parecer do Relator.", "2026-06-03T10:00", URI + "77", ""],
    ["7", "EMC", "1", "2026", "Emenda.", "2026-02-01T10:00", URI + "1", ""],
    ["8", "RIC", "5", "2026", "Requer informações.", "2026-02-02T10:00", "", ""],
    ["9", "RIC", "6", "2026", "Requer informações.", "2026-02-03T10:00", "", ""],
]
AUT_CAB = ["idProposicao", "idDeputadoAutor", "ordemAssinatura", "proponente"]
AUTORES = [
    ["1", "100", "1", "1"],
    ["2", "100", "4", "1"],  # coautor
    ["2", "200", "1", "1"],
    ["3", "100", "1", "1"],
    ["4", "100", "1", "1"],
    ["5", "100", "1", "1"],  # parecer a requerimento de informação: não é relatoria
    ["6", "100", "1", "1"],  # proposta de ano antigo, buscada na API
    ["7", "100", "1", "1"],
    ["8", "100", "1", "1"],
    ["9", "100", "2", "0"],  # só apoio, não conta
    ["1", "999", "1", "1"],  # não está no banco
]


def _politicos():
    with db.sessao() as s:
        for cod in (100, 200):
            s.add(db.Politico(casa="camara", cargo="Deputado Federal", codigo=cod, nome=f"Dep {cod}", uf="SP", em_exercicio=True))


def test_conclusao_do_parecer():
    assert ca.conclusao_parecer("Parecer do Relator, Dep. A (PL-BA), pela aprovação.") == "pela aprovação"
    assert ca.conclusao_parecer("Cria cargos no Ministério.") is None


def test_producao_e_relatorias(client, tmp_path):
    _politicos()
    ca._indice.clear()
    client.bytes(f"{ARQUIVOS}/proposicoes/csv/proposicoes-2026.csv", _csv(PROP_CAB, PROPOSICOES))
    client.bytes(f"{ARQUIVOS}/proposicoesAutores/csv/proposicoesAutores-2026.csv", _csv(AUT_CAB, AUTORES))
    client.rotas[f"{API}/proposicoes/77"] = [({}, ("json", "camara_proposicao_77.json"))]
    assert ca.coletar_proposicoes(client, 2026) == 2

    with db.sessao() as s:
        linhas = {a.codigo_politico: a.dados for a in s.query(db.Atividade).all()}
    d = linhas[100]
    assert [p[1] for p in d["propostas"]] == ["PEC 3/2026", "PL 10/2026"]
    assert d["propostas"][0][5] == 0 and d["propostas"][1][5] == 1
    assert d["emendas"] == 1 and d["requerimentos"] == 1 and d["pedidos_informacao"] == 1
    # Dois pareceres ao PL 10 viram uma relatoria (o mais recente); o parecer ao
    # RIC fica de fora; a proposta antiga vem da API.
    assert [r[1] for r in d["relatorias"]] == ["PL 77/2015", "PL 10/2026"]
    assert d["relatorias"][1][4] == "pela rejeição"
    assert linhas[200]["propostas"][0][5] == 1

    exportar(tmp_path)
    perfil = json.loads((tmp_path / "v1/politicos/camara-100.json").read_text())
    assert perfil["atividade"]["anos"]["2026"]["producao"]["relatorias"][0][1] == "PL 77/2015"
    assert perfil["atividade"]["formato"]["propostas"][0] == "id"


def test_periodos_de_exercicio():
    hist = [
        {"dataHora": "2023-02-01T00:00", "situacao": None},
        {"dataHora": "2023-02-01T12:05", "situacao": "Exercício"},
        {"dataHora": "2024-03-01T10:00", "situacao": "Licença"},
        {"dataHora": "2024-07-01T10:00", "situacao": "Exercício"},
        {"dataHora": "2024-09-10T10:00", "situacao": "Exercício"},  # troca de partido
    ]
    assert ca.periodos_exercicio(hist, hoje=date(2026, 1, 1)) == [
        (date(2023, 2, 1), date(2024, 3, 1)), (date(2024, 7, 1), date(2026, 1, 1)),
    ]


def test_presenca_conta_so_o_periodo_em_exercicio(client):
    _politicos()
    ca._exercicio.clear()
    eventos = _csv(["id", "dataHoraInicio", "situacao", "descricaoTipo"], [
        ["1", "2026-02-03T14:00", "Encerrada", "Sessão Deliberativa"],
        ["2", "2026-02-04T14:00", "Encerrada", "Sessão Deliberativa"],
        ["3", "2026-02-05T14:00", "Cancelada", "Sessão Deliberativa"],
        ["4", "2026-02-05T09:00", "Encerrada (Final)", "Reunião Deliberativa"],
        ["5", "2026-03-10T14:00", "Encerrada", "Sessão Deliberativa"],
    ])
    presencas = _csv(["idEvento", "idDeputado"], [["1", "100"], ["5", "100"], ["4", "100"], ["5", "200"]])
    client.bytes(f"{ARQUIVOS}/eventos/csv/eventos-2026.csv", eventos)
    client.bytes(f"{ARQUIVOS}/eventosPresencaDeputados/csv/eventosPresencaDeputados-2026.csv", presencas)
    client.rotas[f"{API}/deputados/100/historico"] = [({}, ("json", "camara_historico_titular.json"))]
    client.rotas[f"{API}/deputados/200/historico"] = [({}, ("json", "camara_historico_suplente.json"))]
    assert ca.coletar_presenca(client, 2026) == 2
    with db.sessao() as s:
        d = {a.codigo_politico: a.dados for a in s.query(db.Atividade).all()}
    assert d[100] == {"dias_presente": 2, "dias_sessao": 3, "periodo_parcial": False}
    assert d[200] == {"dias_presente": 1, "dias_sessao": 1, "periodo_parcial": True}


def test_resumo_de_discursos():
    r = ca.resumo_discursos([
        {"dataHoraInicio": "2026-03-01T10:00", "tipoDiscurso": "PELA ORDEM", "transcricao": "O SR. FULANO (PL - SP. Sem revisão do orador.) - Sr. Presidente, peço a palavra.", "urlTexto": "u1"},
        {"dataHoraInicio": "2026-05-01T10:00", "tipoDiscurso": "DISCUSSÃO", "sumario": "Defesa do projeto.", "urlTexto": None, "urlVideo": "v2"},
    ])
    assert r["total"] == 2
    assert r["por_tipo"] == {"Pela ordem": 1, "Discussão": 1}
    assert r["recentes"][0] == ["2026-05-01", "Discussão", "Defesa do projeto.", "v2"]
    assert r["recentes"][1][2] == "Sr. Presidente, peço a palavra."


def test_comissoes_juntam_periodos_e_frentes(client, tmp_path):
    _politicos()
    orgaos = ["siglaOrgao", "nomeOrgao", "nomePublicacaoOrgao", "uriDeputado", "cargo", "dataInicio", "dataFim"]
    dep = "https://dadosabertos.camara.leg.br/api/v2/deputados/100"
    client.json(f"{API}/legislaturas", "camara_legislaturas.json")
    client.bytes(f"{ARQUIVOS}/orgaosDeputados/csv/orgaosDeputados-L56.csv", _csv(orgaos, [
        ["CCJC", "Comissão de Constituição e Justiça", "Comissão de Constituição e Justiça", dep, "Suplente", "2019-03-13", "2023-01-31"],
    ]))
    client.bytes(f"{ARQUIVOS}/orgaosDeputados/csv/orgaosDeputados-L57.csv", _csv(orgaos, [
        ["CFT", "Comissão de Finanças", "Comissão de Finanças", dep, "Titular", "2025-03-18", "2026-01-31"],
        ["CFT", "Comissão de Finanças", "Comissão de Finanças", dep, "Titular", "2026-03-18", ""],
        ["CCJC", "Comissão de Constituição e Justiça", "Comissão de Constituição e Justiça", dep, "Suplente", "2023-03-15", "2024-02-04"],
        ["MISSAO", "Bancada do Partido Missão", "Bancada do Partido Missão", dep, "Titular", "2026-01-01", ""],
    ]))
    frentes = ["id", "titulo", "deputado_.id", "deputado_.idLegislatura", "deputado_.titulo"]
    client.bytes(f"{ARQUIVOS}/frentesDeputados/csv/frentesDeputados.csv", _csv(frentes, [
        ["1", "Frente B", "100", "57", "Membro"],
        ["2", "Frente A", "100", "57", "Membro"],
        ["3", "Frente C", "100", "57", "Coordenador"],
        ["4", "Frente Antiga", "100", "56", "Membro"],
    ]))
    assert ca.coletar_comissoes(client) == 1
    exportar(tmp_path)
    a = json.loads((tmp_path / "v1/politicos/camara-100.json").read_text())["atividade"]
    assert a["comissoes"]["itens"] == [
        ["CFT", "Comissão de Finanças", "Titular", "2025-03-18", None],
        ["CCJC", "Comissão de Constituição e Justiça", "Suplente", "2019-03-13", "2024-02-04"],
    ]
    assert a["frentes"]["itens"] == [[3, "Frente C", 1], [2, "Frente A", 0], [1, "Frente B", 0]]
