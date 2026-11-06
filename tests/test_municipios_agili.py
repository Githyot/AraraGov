from datetime import date

from araragov.municipios import agili, md

CLIENTES = [
    {"shortname": "prefguarantanorte-mt", "uf": "MT  ", "municipio": "Guarantã do Norte",
     "nomeRazaoSocial": "PREFEITURA MUNICIPAL DE GUARANTÃ DO NORTE"},
    {"shortname": "camaraguarantanorte-mt", "uf": "MT", "municipio": "Guarantã do Norte"},
    {"shortname": "prefcarlinda-mt", "uf": "MT", "nomeRazaoSocial": "PREFEITURA MUNICIPAL DE CARLINDA"},
    {"shortname": "prefnaoexiste-mt", "uf": "MT", "municipio": "Cidade Que Não Existe"},
]


def _emp(i, doc, nome, pago, natureza="3.3.90.39.99", funcao="04 - Administração"):
    return {"id": i, "numeroAno": f"{i}/2025", "orgao": "02 - GABINETE", "funcao": funcao,
            "subfuncao": "122 - Administração geral", "naturezaDespesa": natureza, "elementoDespesa": "x",
            "nomeFavorecido": nome, "cpfcnpjFavorecido": doc, "empenhado": pago, "liquidado": pago, "pago": pago}


EMPENHOS = [
    _emp(1, "00.703.157/0001-83", "CNM", 4292.5),
    _emp(2, "00.703.157/0001-83", "CNM", 100, natureza="4.4.90.51.99"),
    _emp(3, "080.862.981-67", "FULANA DE TAL", 1114, funcao="10 - Saúde"),
    _emp(4, "00.703.157/0001-83", "CNM", 9, natureza="3.1.90.11.01"),
]


class Client:
    def __init__(self):
        self.pedidos = []

    def get_json(self, url, params=None):
        assert url.endswith("/seletor/get")
        return CLIENTES

    def pedir_json(self, metodo, url, corpo=None, cabecalhos=None):
        self.pedidos.append((metodo, url, cabecalhos.get("uc")))
        if "obterDadosAbaDadosDetalhadosDespesa" in url:
            return {"historico": "Pavimentação da rua B, contrato 12/2025"}
        if cabecalhos["uc"] != "prefguarantanorte-mt":
            return {"data": [], "totalResult": 0}
        assert next(c for c in corpo if c["field"] == "FiltroExercicio")["value"] == "2025"
        pagina = int(url.split("page=")[1].split("&")[0])
        return {"data": EMPENHOS[pagina * 2:pagina * 2 + 2], "totalResult": len(EMPENHOS)}


def test_prefeituras_so_com_codigo_ibge():
    assert agili.prefeituras(Client()) == [("MT", 5102793, "prefcarlinda-mt"), ("MT", 5104104, "prefguarantanorte-mt")]


def test_gerar(tmp_path, monkeypatch):
    monkeypatch.setattr(agili, "TAMANHO_PAGINA", 2)
    c = Client()
    assert agili.gerar(c, tmp_path, [2025], hoje=date(2026, 11, 6)) == 1
    assert sum("page=" in u for _, u, _ in c.pedidos) == 3  # 2 páginas + Carlinda vazia
    texto = (tmp_path / "v1/municipios/mt/5104104/2025-pagamentos.md").read_text(encoding="utf-8")
    assert "08086298167" not in texto and "FULANA" not in texto and "862.981" not in texto
    doc = md.ler(texto)
    assert doc.meta["uf"] == "MT" and doc.meta["municipio"] == "Guarantã Do Norte"
    assert "Agili" in texto
    f = doc.tabelas["favorecidos"][0]
    assert f["cnpj"] == "00.703.157/0001-83" and str(f["pago"]) == "4392.5"
    assert doc.tabelas["obras"][0]["historico"].startswith("Pavimentação da rua B")
    resumo = {r["grupo"].split(" (")[0]: r for r in doc.tabelas["resumo"]}
    assert str(resumo["Pessoas físicas"]["pago"]) == "1114"
    assert str(resumo["Pessoal, encargos e dívida"]["pago"]) == "9"
    assert {a["funcao"] for a in doc.tabelas["areas-favorecidos"]} == {"Administração"}
