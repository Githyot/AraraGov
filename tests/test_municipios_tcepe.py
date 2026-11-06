import json
from datetime import date

from araragov.municipios import md, tcepe

UNIDADES = [
    {"UNIDADEFEDERATIVA": "PE", "MUNICIPIO": "Abreu e Lima", "CODIGOMUNICIPIO": "P001"},
    {"UNIDADEFEDERATIVA": "PE", "MUNICIPIO": "Abreu e Lima", "CODIGOMUNICIPIO": "P001"},
    {"UNIDADEFEDERATIVA": "PE", "MUNICIPIO": "Recife", "CODIGOMUNICIPIO": "P120"},
    {"UNIDADEFEDERATIVA": "PE", "MUNICIPIO": "Governo do Estado", "CODIGOMUNICIPIO": ""},
    {"UNIDADEFEDERATIVA": "PE", "MUNICIPIO": "Belém de São Francisco", "CODIGOMUNICIPIO": "P017"},
]


def _d(i, doc, nome, pago, elemento="Material de Consumo", natureza="Outras Despesas Correntes",
       categoria="Despesa Corrente", funcao="Administração", historico=""):
    return {"ID_EMPENHO": f"{i}   ", "NUMEROEMPENHO": f"{i:06d}", "CPF_CNPJ": doc, "FORNECEDOR": nome,
            "VALORPAGO": pago, "ELEMENTODESPESA": elemento, "NATUREZA": natureza, "CATEGORIA": categoria,
            "FUNCAO": funcao, "SUBFUNCAO": "Administração Geral", "NOMEUNIDADEGESTORA": "Prefeitura",
            "ACAO": "Apoio", "HISTORICO": historico}


ABREU = [
    _d(1, "00703157000183", "CNM", "4292.50"),
    _d(2, "00703157000183", "CNM", "100.00", elemento="Obras e Instalações", natureza="Investimentos",
       categoria="Despesa de Capital", historico="Pavimentação da rua B"),
    _d(3, "08086298   ", "FULANA DE TAL", "1114.00", funcao="Saúde"),
    {**_d(5, "00703157000183", "CICLANO", "50.00"), "TIPOCREDOR": "1"},
    _d(4, "00703157000183", "CNM", "9.00", elemento="Vencimentos e Vantagens Fixas - Pessoal Civil",
       natureza="Pessoal e Encargos Sociais"),
]


class Client:
    def __init__(self, limite=100000):
        self.limite = limite
        self.pedidos = []

    def get_bytes(self, url, params=None):
        self.pedidos.append(dict(params or {}))
        if url == tcepe.UNIDADES:
            conteudo = UNIDADES
        elif params["CODIGO_MUNICIPIO"] == "P001":
            mes = params.get("MESREFERENCIA")
            conteudo = ABREU if mes is None else {1: ABREU[:3], 2: ABREU[3:4]}.get(mes, [])
        else:
            conteudo = []
        r = {"resposta": {"status": "OK", "limiteResultado": str(self.limite), "conteudo": conteudo}}
        return json.dumps(r, ensure_ascii=False).encode("latin-1")


def test_codigos():
    assert tcepe.codigos(Client()) == {"P001": (2600054, "Abreu e Lima"), "P017": (2601607, "Belém do São Francisco"),
                                     "P120": (2611606, "Recife")}


def test_gerar(tmp_path):
    assert tcepe.gerar(Client(), tmp_path, [2025], hoje=date(2026, 11, 6)) == 1
    texto = (tmp_path / "v1/municipios/pe/2600054/2025-pagamentos.md").read_text(encoding="utf-8")
    assert "08086298" not in texto and "FULANA" not in texto and "CICLANO" not in texto
    doc = md.ler(texto)
    assert doc.meta["uf"] == "PE" and "TCE-PE" in texto
    f = doc.tabelas["favorecidos"][0]
    assert f["cnpj"] == "00.703.157/0001-83" and str(f["pago"]) == "4392.5"
    assert doc.tabelas["obras"][0]["historico"] == "Pavimentação da rua B"
    resumo = {r["grupo"].split(" (")[0]: r for r in doc.tabelas["resumo"]}
    assert str(resumo["Pessoas físicas"]["pago"]) == "1164"
    assert str(resumo["Pessoal, encargos e dívida"]["pago"]) == "9"


def test_municipio_grande_e_pedido_mes_a_mes(tmp_path):
    c = Client(limite=4)
    assert tcepe.gerar(c, tmp_path, [2025], limite_municipios=1, hoje=date(2026, 11, 6)) == 1
    meses = [p.get("MESREFERENCIA") for p in c.pedidos if p.get("CODIGO_MUNICIPIO") == "P001"]
    assert meses == [None] + list(range(1, 13))


def test_lista_fora_do_ar_usa_copia_publicada(tmp_path):
    from araragov.municipios import publicados

    class SemLista(Client):
        def get_bytes(self, url, params=None):
            if url == tcepe.UNIDADES:
                raise RuntimeError("503")
            if url == f"{publicados.PUBLICADO}/{tcepe.CODIGOS_PUBLICADOS}":
                return json.dumps({"P001": [2600054, "Abreu e Lima"]}).encode()
            return super().get_bytes(url, params)

    assert tcepe.gerar(SemLista(), tmp_path, [2025], hoje=date(2026, 11, 6)) == 1
    assert json.loads((tmp_path / tcepe.CODIGOS_PUBLICADOS).read_text())["P001"][0] == 2600054
