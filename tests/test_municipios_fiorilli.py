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
        "https://anapolis.go.gov.br": Resp(200, '[{"exercicio": "2025"}]'),
        "https://transparencia.goias.go.gov.br": Resp(200, "<html>Just a moment...</html>"),
    })
    achados = fiorilli.descobrir(["GO"], 2025, trabalhadores=2, sessao=s)
    assert achados == [{"uf": "GO", "ibge": "5201108", "municipio": "Anápolis", "site": "https://anapolis.go.gov.br"}]
    assert not any("/x." in p for p in s.pedidos)
    texto = fiorilli.escrever_lista(achados)
    assert texto.splitlines()[1] == "uf;ibge;municipio;site" and "5201108" in texto
