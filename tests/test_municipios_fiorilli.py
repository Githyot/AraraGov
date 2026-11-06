from araragov.municipios import fiorilli


class Resp:
    def __init__(self, status, texto):
        self.status_code, self.text = status, texto


class Sessao:
    def __init__(self, respostas):
        self.respostas, self.headers, self.pedidos = respostas, {}, []

    def get(self, url, params=None, timeout=None, allow_redirects=True):
        self.pedidos.append(url)
        for prefixo, r in self.respostas.items():
            if url.startswith(prefixo):
                return r
        raise fiorilli.requests.ConnectionError("sem rota")


def test_candidatos():
    c = fiorilli.candidatos("GO", "Águas Lindas de Goiás")
    assert c[0] == "https://transparencia.aguaslindasdegoias.go.gov.br"
    assert "http://aguaslindasdegoias.go.gov.br:8079" in c


def test_descobrir_aceita_so_json(monkeypatch):
    monkeypatch.setattr(fiorilli, "municipios_ibge", lambda: {
        ("GO", "ANAPOLIS"): (5201108, "Anápolis"), ("GO", "GOIAS"): (5208905, "Goiás"), ("MG", "X"): (1, "X")})
    s = Sessao({
        "https://anapolis.go.gov.br": Resp(200, "<HTML><head><TITLE>Dados Abertos Portal Transparência Fiorilli - Despesas</TITLE>"),
        "https://transparencia.goias.go.gov.br": Resp(200, "<html>Just a moment...</html>"),
    })
    achados = fiorilli.descobrir(["GO"], 2025, trabalhadores=2, sessao=s)
    assert achados == [{"uf": "GO", "ibge": "5201108", "municipio": "Anápolis", "site": "https://anapolis.go.gov.br"}]
    assert not any("/x." in p for p in s.pedidos)
    texto = fiorilli.escrever_lista(achados)
    assert texto.splitlines()[1] == "uf;ibge;municipio;site" and "5201108" in texto


def test_lista_empacotada():
    portais = fiorilli.lista()
    assert portais and all(p["site"].startswith("http") and p["ibge"].isdigit() for p in portais)


def test_gerar(tmp_path, monkeypatch):
    from datetime import date

    from araragov.municipios import md

    monkeypatch.setattr(fiorilli, "lista", lambda: [{"uf": "MA", "ibge": "2105302", "municipio": "Imperatriz",
                                                     "site": "http://x:8079"}])
    linhas = [
        {"EMPRESA": "2", "CODIGO": "1", "NOMEFOR": "CNM", "CPFFORMATADO": "00.703.157/0001-83", "PAGO": "4.292,50",
         "CATEC": "3.3.90.39.99", "NATUREZA": "SERV", "FUNCAONOME": "Administração", "SUBFUNCAONOME": "Adm",
         "NOMEEMPRESA": "PREFEITURA", "PRODU": "x"},
        {"EMPRESA": "2", "CODIGO": "2", "NOMEFOR": "CNM", "CPFFORMATADO": "00.703.157/0001-83", "PAGO": "100,00",
         "CATEC": "4.4.90.51.99", "NATUREZA": "OBRAS", "FUNCAONOME": "Urbanismo", "SUBFUNCAONOME": "Infra",
         "NOMEEMPRESA": "PREFEITURA", "PRODU": "Pavimentação da rua B"},
        {"empresa": "2", "codigo": "3", "nomefor": "FULANA", "cpfformatado": "***.862.981-**", "pago": "1.114,00",
         "catec": "3.3.90.36.99", "funcaonome": "Saúde"},
    ]

    class C:
        def get_json(self, url, params=None):
            assert url == "http://x:8079/Transparencia/VersaoJson/Despesas/" and params["Exercicio"] == 2025
            return linhas

    assert fiorilli.gerar(C(), tmp_path, [2025], hoje=date(2026, 11, 6)) == 1
    texto = (tmp_path / "v1/municipios/ma/2105302/2025-pagamentos.md").read_text(encoding="utf-8")
    assert "FULANA" not in texto and "862.981" not in texto and "Fiorilli" in texto
    doc = md.ler(texto)
    assert str(doc.tabelas["favorecidos"][0]["pago"]) == "4392.5"
    assert doc.tabelas["obras"][0]["historico"] == "Pavimentação da rua B"
    resumo = {r["grupo"].split(" (")[0]: r for r in doc.tabelas["resumo"]}
    assert str(resumo["Pessoas físicas"]["pago"]) == "1114"


def test_valor_br():
    assert fiorilli._valor_br("1234.5") == "1234,5"
    assert fiorilli._valor_br("1.234,56") == "1.234,56"
    assert fiorilli._valor_br("123000") == "123000"
    assert fiorilli._valor_br("1.234.567") == "1.234.567"
