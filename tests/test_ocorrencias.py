import csv
import io
import json
import zipfile
from datetime import date

from sqlalchemy import select

from araragov import db
from araragov.collectors import ocorrencias as oc
from araragov.collectors._comum import gravar_politico
from araragov.collectors.tse import CANDIDATOS_URL
from araragov.exportar import exportar, processos_curados

HOJE = date(2026, 11, 6)
CPF_MARIA = "12345678901"

CAMPOS_CAND = ["SG_UF", "SG_UE", "CD_ELEICAO", "SQ_CANDIDATO", "DS_CARGO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
               "NR_CPF_CANDIDATO", "DS_DETALHE_SITUACAO_CAND"]
CAMPOS_SANCAO = ["CADASTRO", "TIPO DE PESSOA", "CPF OU CNPJ DO SANCIONADO", "NOME DO SANCIONADO", "CATEGORIA DA SANÇÃO",
                 "DATA INÍCIO SANÇÃO", "DATA FINAL SANÇÃO", "ÓRGÃO SANCIONADOR", "NÚMERO DO PROCESSO", "FUNDAMENTAÇÃO LEGAL"]


def _zip(nome, campos, linhas):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        s = io.StringIO()
        w = csv.writer(s, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(campos)
        w.writerows(linhas)
        z.writestr(nome, s.getvalue().encode("latin-1"))
    return buf.getvalue()


def _politicos():
    with db.sessao() as s:
        gravar_politico(s, {"casa": "camara", "cargo": "Deputado Federal", "codigo": 1, "nome": "Maria Saúde",
                            "nome_civil": "Maria da Silva", "uf": "MG", "partido": "PT", "em_exercicio": True})
        gravar_politico(s, {"casa": "camara", "cargo": "Deputado Federal", "codigo": 2, "nome": "Zé",
                            "nome_civil": "José Souza", "uf": "SP", "partido": "PL", "em_exercicio": True})
        gravar_politico(s, {"casa": "al-rj", "cargo": "Deputado estadual", "codigo": 3, "nome": "Ana",
                            "nome_civil": "Ana Lima", "uf": "RJ", "partido": "PSD", "em_exercicio": True})


def _rotas(client):
    client.bytes(CANDIDATOS_URL.format(ano=2022), _zip("consulta_cand_2022_MG.csv", CAMPOS_CAND, [
        ["MG", "MG", "546", "100", "DEPUTADO FEDERAL", "MARIA DA SILVA", "MARIA SAÚDE", CPF_MARIA, "DEFERIDO COM RECURSO"],
        # Mesma pessoa (mesmo CPF) concorreu a outro cargo e teve o registro indeferido.
        ["SP", "SP", "546", "101", "GOVERNADOR", "MARIA DA SILVA", "MARIA", CPF_MARIA, "INDEFERIDO"],
        ["SP", "SP", "546", "200", "DEPUTADO FEDERAL", "JOSE SOUZA", "ZÉ", "-4", "DEFERIDO"],
        # Dois "Ana Lima" no RJ com CPFs diferentes: ambíguo, não cruza.
        ["RJ", "RJ", "546", "300", "DEPUTADO ESTADUAL", "ANA LIMA", "ANA", "22222222222", "DEFERIDO"],
        ["RJ", "RJ", "546", "301", "DEPUTADO ESTADUAL", "ANA LIMA", "ANA LIMA", "33333333333", "DEFERIDO"],
    ]))
    client.bytes(oc.MOTIVO_CASSACAO_URL.format(ano=2022), _zip("motivo_cassacao_2022_BRASIL.csv",
                 ["SQ_CANDIDATO", "DS_MOTIVO_CASSACAO"], [["101", "FICHA LIMPA"]]))
    for cadastro in ("ceis", "cnep"):
        linhas = [] if cadastro == "cnep" else [
            ["CEIS", "F", "***.456.789-**", "MARIA DA SILVA", "Proibição - Lei de Improbidade", "01/02/2020", "01/02/2025",
             "TJMG", "500-1", "Lei 8.429/1992"],
            # Homônima: nome igual, CPF diferente. Não pode aparecer.
            ["CEIS", "F", "***.000.111-**", "MARIA DA SILVA", "Impedimento", "01/02/2024", "", "Prefeitura X", "9", ""],
            ["CEIS", "F", "***.456.789-**", "JOSE SOUZA", "Impedimento", "01/02/2024", "", "Prefeitura Y", "8", ""],
        ]
        client.bytes(oc.SANCOES_URL.format(cadastro=cadastro, data="20261105"),
                     _zip(f"2026_{cadastro}.csv", CAMPOS_SANCAO, linhas))
    client.json(oc.TCU_URL, "tcu_inabilitados.json")


def test_cpf_confere():
    assert oc.cpf_confere("***.456.789-**", CPF_MARIA)
    assert not oc.cpf_confere("***.456.780-**", CPF_MARIA)
    assert not oc.cpf_confere("***.***.789-**", CPF_MARIA)  # poucos dígitos visíveis
    assert oc.cpf_confere("123.456.789-01", CPF_MARIA)
    assert not oc.cpf_confere("***.456.789-**", None)
    assert oc.cpf_valido("-4") is None and oc.cpf_valido("00000000000") is None


def test_coleta_cruza_sem_homonimos(client):
    _politicos()
    _rotas(client)
    assert oc.coletar(client, anos=(2022,), hoje=HOJE) == 4
    with db.sessao() as s:
        por = {}
        for o in s.execute(select(db.Ocorrencia)).scalars():
            por.setdefault(o.codigo_politico, []).append(o)
        verif = {(v.codigo_politico, v.fonte) for v in s.execute(select(db.VerificacaoOcorrencia)).scalars()}
        tudo = " ".join(str(vars(o)) for lista in por.values() for o in lista)
    maria = {(o.fonte, o.tipo, o.situacao) for o in por[1]}
    assert maria == {
        ("tse", "candidatura", "em_andamento"), ("tse", "candidatura", "decidido"),
        ("tse", "certidoes", "informativo"), ("cgu", "sancao", "sancao_encerrada"), ("tcu", "inabilitacao", "sancao_vigente"),
    }
    indeferida = next(o for o in por[1] if o.situacao == "decidido")
    assert "Ficha limpa" in indeferida.descricao and indeferida.link.endswith("/2022/546/SP/101")
    # José: sem CPF no TSE, então a sanção com nome igual NÃO é ligada a ele.
    assert {o.tipo for o in por[2]} == {"certidoes"}
    assert (2, "tse") in verif and (2, "cgu") not in verif and (1, "cgu") in verif
    # Ana: nome ambíguo, nada cruzado.
    assert 3 not in por
    # Nenhum CPF gravado.
    assert CPF_MARIA not in tudo and "456789" not in tudo


def test_exporta_ocorrencias(client, tmp_path, monkeypatch):
    _politicos()
    _rotas(client)
    oc.coletar(client, anos=(2022,), hoje=HOJE)
    exportar(tmp_path)
    maria = json.loads((tmp_path / "v1/politicos/camara-1.json").read_text())["ocorrencias"]
    assert len(maria["itens"]) == 4 and len(maria["certidoes"]) == 2  # deputada e governadora
    assert "inocentes" in maria["aviso"]
    assert all(f["conferido"] for f in maria["fontes"])
    jose = json.loads((tmp_path / "v1/politicos/camara-2.json").read_text())["ocorrencias"]
    assert jose["itens"] == []
    assert {f["fonte"]: f["conferido"] for f in jose["fontes"]} == {"tse": True, "cgu": False, "tcu": False}
    resumo = json.loads((tmp_path / "v1/politicos.json").read_text())
    assert all("ocorrencias" not in r for r in resumo)  # nada de selo ou ranking na lista


def test_lista_curada_so_aceita_fonte_oficial(tmp_path):
    arq = tmp_path / "processos.csv"
    arq.write_text(
        "casa;nome;tipo;titulo;situacao;data;orgao;processo;descricao;fonte\n"
        "camara;Maria Saúde;acao_penal;Ação penal;absolvido;2024-03-01;STF;AP 1;;https://portal.stf.jus.br/processos/x\n"
        "camara;Maria Saúde;acao_penal;Notícia;condenado;2024-03-01;;;;https://jornal.com.br/x\n"
        "camara;Maria Saúde;acao_penal;Sem situação;culpado;2024-03-01;;;;https://www.tjmg.jus.br/x\n"
        "camara;Maria Saúde;acao_penal;Falso domínio;arquivado;2024-03-01;;;;https://stf.jus.br.exemplo.com/x\n",
        encoding="utf-8",
    )
    por = processos_curados(arq)
    assert [i["titulo"] for i in por[("camara", "maria saude")]] == ["Ação penal"]
