import json
from datetime import date

from araragov.collectors import camara, referencia
from araragov.exportar import exportar

from .conftest import FIXTURES, zip_de


def test_exporta_lista_e_perfil(client, tmp_path):
    client.json(f"{camara.API}/legislaturas", "camara_legislaturas.json")
    url = f"{camara.API}/deputados"
    client.json(url, "camara_deputados_leg57.json", {"idLegislatura": 57, "pagina": 1})
    client.json(url, "camara_deputados_leg57_p2.json", {"idLegislatura": 57, "pagina": 2})
    client.json(url, "camara_deputados_atuais.json", {"pagina": 1})
    camara.coletar_deputados(client)
    for nome in ("votacoes", "votacoesVotos", "votacoesProposicoes", "votacoesOrientacoes"):
        client.bytes(f"{camara.ARQUIVOS}/{nome}/csv/{nome}-2025.csv", (FIXTURES / f"{nome}-2025.csv").read_bytes())
    camara.coletar_votacoes(client, 2025)
    client.bytes(camara.CEAP_URL.format(ano=2025), zip_de(FIXTURES / "cota_camara_2025.csv"))
    camara.coletar_despesas(client, 2025)
    referencia.carregar_subsidios()
    client.json(referencia.IPCA_URL, "ipca.json")
    referencia.coletar_ipca(client, ate=date(2024, 3, 31))

    assert exportar(tmp_path) == 3
    lista = json.loads((tmp_path / "v1/politicos.json").read_text())
    assert {p["id"] for p in lista} == {"camara-204554", "camara-62881", "camara-220593"}

    perfil = json.loads((tmp_path / "v1/politicos/camara-62881.json").read_text())
    assert perfil["salario"]["atual"] == 46366.19
    assert perfil["gastos"]["total"] == 3152.28
    assert sum(a["total"] for a in perfil["gastos"]["anos"].values()) == 3152.28
    assert perfil["votacoes"][0]["voto"] == "sim"
    assert perfil["votacoes"][0]["proposicao"] == "PL 1/2025"
    assert perfil["presenca"] == {"sim": 1}
    assert json.loads((tmp_path / "v1/meta.json").read_text())["total_politicos"] == 3


def test_exporta_estaduais(client, tmp_path):
    from araragov import db

    referencia.carregar_subsidios()
    client.json(referencia.IPCA_URL, "ipca.json")
    referencia.coletar_ipca(client, ate=date(2024, 3, 31))
    with db.sessao() as s:
        s.add(db.Politico(casa="al-mg", cargo="Deputado estadual", codigo=12193, nome="A", uf="MG"))
        s.add(db.Politico(casa="gov-sp", cargo="Governador", codigo=100, nome="B", uf="SP", fonte="tse"))
    assert exportar(tmp_path) == 2
    lista = {p["id"]: p for p in json.loads((tmp_path / "v1/politicos.json").read_text())}
    assert lista["al-mg-12193"]["esfera"] == "estadual"
    assert lista["al-mg-12193"]["orgao"] == "Assembleia Legislativa (MG)"
    assert lista["gov-sp-100"]["orgao"] == "Governo do estado (SP)"
    dep = json.loads((tmp_path / "v1/politicos/al-mg-12193.json").read_text())
    assert dep["salario"]["atual"] == 34774.64
    assert dep["salario"]["teto"] is True and "75%" in dep["salario"]["observacao"]
    gov = json.loads((tmp_path / "v1/politicos/gov-sp-100.json").read_text())
    assert gov["salario"]["atual"] is None and gov["salario"]["observacao"]
    assert gov["aviso_cadastro"] and dep["aviso_cadastro"] is None


def test_exporta_custo_do_gabinete_e_beneficios(tmp_path):
    from decimal import Decimal

    from araragov import db

    with db.sessao() as s:
        s.add(db.Politico(casa="senado", cargo="Senador", codigo=475, nome="Confúcio Moura", uf="RO"))
        s.add(db.Assessor(casa="senado", codigo_politico=475, nome="A", remuneracao=Decimal("12000.50"), remuneracao_ref="2026-09"))
        s.add(db.Assessor(casa="senado", codigo_politico=475, nome="B", remuneracao=Decimal("3000"), remuneracao_ref="2026-09"))
        s.add(db.Assessor(casa="senado", codigo_politico=475, nome="C"))
        s.add(db.Beneficio(casa="senado", codigo_politico=475, tipo="imovel_funcional", descricao="Ocupa imóvel funcional em Brasília"))
    exportar(tmp_path)
    perfil = json.loads((tmp_path / "v1/politicos/senado-475.json").read_text())
    assert perfil["custo_gabinete"] == {"mensal": 15000.5, "pessoas_com_valor": 2, "pessoas": 3, "referencia": "2026-09", "origem": "folha"}
    assert perfil["beneficios"][0]["tipo"] == "imovel_funcional"
    assert {g["nome"]: g["remuneracao"] for g in perfil["gabinete"]} == {"A": 12000.5, "B": 3000.0, "C": None}


def test_doacao_de_salario_declarada(tmp_path):
    from araragov import db
    from araragov.exportar import doacoes_salario

    lista = doacoes_salario()
    assert lista[("camara", "kim kataguiri")]["parte"] == "20%"
    assert all(d["fonte"].startswith("http") for d in lista.values())

    with db.sessao() as s:
        s.add(db.Politico(casa="camara", cargo="Deputado Federal", codigo=204536, nome="Kim Kataguiri", uf="SP"))
        s.add(db.Politico(casa="camara", cargo="Deputado Federal", codigo=1, nome="Outra Pessoa", uf="SP"))
    exportar(tmp_path)
    resumo = {p["id"]: p for p in json.loads((tmp_path / "v1/politicos.json").read_text())}
    assert resumo["camara-204536"]["doa_salario"] is True
    assert resumo["camara-1"]["doa_salario"] is False
    perfil = json.loads((tmp_path / "v1/politicos/camara-204536.json").read_text())
    assert perfil["doacao_salario"]["fonte"].startswith("https://")
    assert json.loads((tmp_path / "v1/politicos/camara-1.json").read_text())["doacao_salario"] is None
