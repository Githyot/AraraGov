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
    assert perfil["votacoes"][0]["voto"] == "sim"
    assert perfil["votacoes"][0]["proposicao"] == "PL 1/2025"
    assert perfil["presenca"] == {"sim": 1}
    assert json.loads((tmp_path / "v1/meta.json").read_text())["total_politicos"] == 3
