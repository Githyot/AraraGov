from datetime import date
from decimal import Decimal

from araragov.municipios import financas, md

S = financas.SICONFI


class Cliente:
    """Responde por URL + parâmetros, sem depender de arquivos."""

    def __init__(self, rotas, bytes_=None):
        self.rotas = rotas
        self.bytes_ = bytes_ or {}
        self.chamadas = []

    def get_json(self, url, params=None):
        params = params or {}
        self.chamadas.append((url, params))
        if url == financas.IPCA_URL:
            return [{"data": "01/01/2025", "valor": "1.00"}, {"data": "01/02/2025", "valor": "1.00"}]
        if url == f"{S}/entes":
            return {"items": [
                {"cod_ibge": 4104303, "ente": "Campo Mourão", "uf": "PR", "esfera": "M", "populacao": 99432},
                {"cod_ibge": 41, "ente": "Paraná", "uf": "PR", "esfera": "E"},
                {"cod_ibge": 4100103, "ente": "Abatiá", "uf": "PR", "esfera": "M"},
            ], "hasMore": False}
        chave = (params.get("id_ente"), params.get("an_exercicio"), params.get("no_anexo"), params.get("offset", 0))
        return self.rotas.get(chave, {"items": [], "hasMore": False})

    def get_bytes(self, url, params=None):
        if url in self.bytes_:
            return self.bytes_[url]
        raise RuntimeError("404")


def _i(conta, coluna, valor, cod=None):
    return {"conta": conta, "coluna": coluna, "valor": valor, "cod_conta": cod}


RECEITAS = [
    _i("1.0.0.0.00.0.0 Receitas Correntes", "Receitas Brutas Realizadas", 1000, "RO1.0.0.0.00.0.0"),
    _i("1.0.0.0.00.0.0 Receitas Correntes", "Deduções - FUNDEB", -100, "RO1.0.0.0.00.0.0"),
    _i("1.1.1.2.50.0.0 Imposto sobre a Propriedade Predial e Territorial Urbana", "Receitas Brutas Realizadas", 50.5, "RO1.1.1.2.50.0.0"),
    _i("1.1.1.2.50.1.1 IPTU - Principal", "Receitas Brutas Realizadas", 40, "RO1.1.1.2.50.1.1"),
    _i("1.7.1.8.01.2.0 Cota-Parte do Fundo de Participação dos Municípios", "Receitas Brutas Realizadas", 300, "RO1.7.1.8.01.2.0"),
    _i("Total Receitas", "Receitas Brutas Realizadas", 1000),
]
FUNCOES = [
    _i("10 - Saúde", "Despesas Empenhadas", 500),
    _i("10 - Saúde", "Despesas Pagas", 400),
    _i("10 - Saúde", "Despesas Pagas", 10),  # intraorçamentária, somada
    _i("10.301 - Atenção Básica", "Despesas Liquidadas", 300),
    _i("Despesas Exceto Intraorçamentárias", "Despesas Pagas", 410),
    _i("15 - Urbanismo", "Inscrição de Restos a Pagar Não Processados", 99),
]


def test_receitas_e_destaques():
    linhas = financas.receitas(RECEITAS)
    por = {l["codigo"]: l for l in linhas}
    assert por["1.0.0.0.00.0.0"]["liquida"] == Decimal(900) and por["1.0.0.0.00.0.0"]["nivel"] == 1
    assert "1.1.1.2.50.1.1" not in por  # nível 7 (principal, multa, juros): detalhado demais
    assert por["1.1.1.2.50.0.0"]["conta"].startswith("Imposto sobre a Propriedade")
    d = {x["destaque"]: x for x in financas.destaques(linhas)}
    assert d["IPTU"]["liquida"] == Decimal("50.5") and d["FPM"]["liquida"] == Decimal(300)


def test_areas():
    a = financas.areas(FUNCOES)
    assert [(x["funcao"], x["subfuncao"], x["area"]) for x in a] == [("10", None, "Saúde"), ("10", "301", "Atenção Básica")]
    assert a[0]["pago"] == Decimal(410) and a[0]["empenhado"] == Decimal(500)


def test_gerar_com_sem_dados_e_reaproveitamento(tmp_path):
    rotas = {
        (4104303, 2024, financas.ANEXO_RECEITAS, 0): {"items": RECEITAS[:3], "hasMore": True},
        (4104303, 2024, financas.ANEXO_RECEITAS, 3): {"items": RECEITAS[3:], "hasMore": False},
        (4104303, 2024, financas.ANEXO_FUNCOES, 0): {"items": FUNCOES, "hasMore": False},
    }
    antigo = md.escrever({"tipo": "municipio-ano", "ano": 2020}, {"areas": [{"funcao": "10", "pago": 1}]})
    publicado = {f"{financas.PUBLICADO}/v1/municipios/pr/4104303/2020.md": antigo.encode()}
    r = financas.gerar(lambda: Cliente(rotas, publicado), tmp_path, anos=[2020, 2024], ufs=["PR"],
                       hoje=date(2025, 11, 5), trabalhadores=1)
    assert r == {"siconfi": 3, "reaproveitados": 1, "pendentes": 0}

    base = tmp_path / "v1/municipios/pr"
    doc = md.ler((base / "4104303/2024.md").read_text(encoding="utf-8"))
    assert doc.meta["ipca_fator"] == "1.0201" and doc.meta["ipca_ate"] == "2025-02"
    assert doc.meta["populacao"] == "99432"
    assert doc.tabelas["destaques"][0]["destaque"] == "IPTU"
    assert len(doc.tabelas["receitas"]) == 3  # paginação juntou as duas páginas
    assert (base / "4104303/2020.md").read_text(encoding="utf-8") == antigo

    # Abatiá não entregou: aviso com a prefeitura como responsável
    falta = md.ler((base / "4100103/2020.md").read_text(encoding="utf-8")).tabelas["sem-dados"]
    assert falta[0]["esfera"] == "municipal" and falta[0]["responsavel"] == "Prefeitura de Abatiá (PR)"
    assert falta[0]["obrigacao"].startswith("Lei de Responsabilidade Fiscal")


def test_ano_no_prazo_nao_aponta_falha(tmp_path):
    financas.gerar(lambda: Cliente({}), tmp_path, anos=[2024], ufs=["PR"], hoje=date(2025, 3, 1), trabalhadores=1)
    falta = md.ler((tmp_path / "v1/municipios/pr/4104303/2024.md").read_text(encoding="utf-8")).tabelas["sem-dados"]
    assert falta[0]["obrigacao"] is None and "prazo" in falta[0]["motivo"]


def test_limite_deixa_para_a_proxima(tmp_path):
    r = financas.gerar(lambda: Cliente({}), tmp_path, anos=[2024], ufs=["PR"], hoje=date(2026, 1, 1),
                       limite_siconfi=1, trabalhadores=2)
    assert r == {"siconfi": 1, "reaproveitados": 0, "pendentes": 1}
