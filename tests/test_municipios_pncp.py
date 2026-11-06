from datetime import date
from decimal import Decimal as D

from araragov.municipios import md, pncp


def _contrato(n, ibge="4208203", uf="SC", ni="18356265000192", tipo="PJ", objeto="LOCAÇÃO DE VEÍCULOS",
              valor=1000.0, esfera="M", compra="83102277000152-1-000011/2025", emenda=None):
    return {"orgaoEntidade": {"cnpj": "83102277000152", "razaoSocial": "MUNICIPIO DE ITAJAI", "esferaId": esfera},
            "unidadeOrgao": {"ufSigla": uf, "municipioNome": "Itajaí", "codigoIbge": ibge, "nomeUnidade": "PREFEITURA"},
            "anoContrato": 2025, "numeroControlePNCP": f"83102277000152-2-{n:06d}/2025", "tipoPessoa": tipo,
            "niFornecedor": ni, "nomeRazaoSocialFornecedor": "EMPRESA 12345678901", "valorGlobal": valor,
            "numeroContratoEmpenho": f"{n}/2025", "objetoContrato": objeto, "dataAssinatura": "2025-02-28",
            "numeroControlePncpCompra": compra, "emendaParlamentar": emenda}


class _Cliente:
    def __init__(self, paginas, itens):
        self.paginas, self.itens, self.pedidos = paginas, itens, []

    def get_json(self, url, params=None):
        self.pedidos.append(url)
        if "/itens" in url:
            return self.itens
        return self.paginas.pop(0) if self.paginas else {"data": [], "paginasRestantes": 0}


def test_compra_e_agregar():
    assert pncp._compra("83102277000152-1-000011/2025") == ("83102277000152", 2025, 11)
    linhas = [
        _contrato(1, emenda="202512340001"),
        _contrato(1),  # repetido
        _contrato(2, tipo="PF", ni="12345678901"),
        _contrato(3, uf="SP", ibge="3500105"),  # SP vem do TCE
        _contrato(4, esfera="E"),  # estadual
        _contrato(5, objeto="Recapeamento asfáltico da Rua A", valor=300000.0, compra="83102277000152-1-000020/2025"),
    ]
    diretas = {"83102277000152-1-000011/2025": "Dispensa (Lei 14.133/2021, Art. 75, II)"}
    por = pncp.agregar(linhas, 2025, diretas)
    m = por[4208203]
    assert len(m["contratos"]) == 3
    c1 = next(c for c in m["contratos"] if c["contrato"] == "1/2025")
    assert c1["emenda"] == "202512340001" and c1["modalidade"] == "Dispensa"
    pf = next(c for c in m["contratos"] if c["contrato"] == "2/2025")
    assert pf["cnpj"] is None and pf["empresa"] == "Pessoa física (sem nome)"
    assert m["diretas"]["18356265000192"]["n"] == 1
    assert [o["item"] for o in m["obras"]] == ["recape-cbuq"]


def test_obra_com_quantidade_dos_itens(tmp_path):
    ref = tmp_path / "v1" / "referencia" / "custos"
    ref.mkdir(parents=True)
    (ref / "sc.md").write_text(md.escrever({"tipo": "custos-referencia"}, {"referencias": [
        {"item": "recape-cbuq", "ano": 2025, "minimo": "40", "maximo": "60", "nivel": "1"}]}), encoding="utf-8")
    por = pncp.agregar([_contrato(5, objeto="Recapeamento asfáltico", valor=300000.0)], 2025, {})
    cliente = _Cliente([], [{"unidadeMedida": "M2", "quantidade": 3000.0}, {"unidadeMedida": "UN", "quantidade": 1}])
    pncp.completar_obras(cliente, por, 2025, tmp_path, {"recape-cbuq": "m²"}, limite_itens=10)
    o = por[4208203]["obras"][0]
    assert o["quantidade"] == D("3000") and o["valor_unitario"] == D("100.00")
    assert o["comparacao"] == "66.7% acima da faixa de referência"
    assert "/compras/2025/11/itens" in cliente.pedidos[0]


def test_gerar_escreve_md(tmp_path):
    paginas = [{"data": [], "paginasRestantes": 0}] * 2 + [{"data": [_contrato(1)], "paginasRestantes": 0}]
    cliente = _Cliente(list(paginas), [])
    n = pncp.gerar(cliente, tmp_path, [2025], hoje=date(2025, 1, 5), dias=3)
    assert n == 1
    doc = md.ler((tmp_path / "v1/municipios/sc/4208203/2025-contratos.md").read_text(encoding="utf-8"))
    assert doc.meta["uf"] == "SC" and doc.tabelas["contratos"][0]["empresa"] == "EMPRESA"
    assert doc.tabelas["sem-dados"][0]["responsavel"] == "Prefeitura"


def test_pagina_menor_quando_a_api_recusa(monkeypatch):
    import requests

    from araragov.municipios import pncp

    monkeypatch.setattr(pncp, "_TAMANHOS", {})
    pedidos = []

    class C:
        def get_json(self, url, params):
            pedidos.append(params["tamanhoPagina"])
            if params["tamanhoPagina"] > 50:
                r = requests.Response()
                r.status_code = 400
                raise requests.HTTPError(response=r)
            return {"data": [{"x": 1}], "paginasRestantes": 0}

    assert list(pncp._paginas(C(), "contratacoes/publicacao", {})) == [{"x": 1}]
    assert pedidos == [500, 50]


def test_diretas_com_prazo_esgotado_saem_incompletas():
    from datetime import date as d

    from araragov.municipios import pncp as p

    class Nada:
        def get_json(self, url, params=None):
            raise AssertionError("não deveria pedir nada depois do prazo")

    diretas, completas = p.compras_diretas(Nada(), d(2025, 1, 1), d(2025, 1, 14), minutos=-1)
    assert diretas == {} and completas is False
    texto = p._com_sem_dados(p.documento(1, "X", 2025, {"contratos": [], "obras": [], "diretas": {}}, d(2026, 11, 6),
                                         uf="SC", fonte=p.FONTE, colunas_contratos=p.COLUNAS_CONTRATOS_PNCP),
                             d(2026, 11, 6), False)
    assert "pode estar incompleta" in texto


def test_semana_com_erro_nao_derruba_as_outras():
    from datetime import date as d

    from araragov.municipios import pncp as p

    class Metade:
        def get_json(self, url, params=None):
            if params["dataInicial"] == "20250101":
                raise RuntimeError("503")
            return {"data": [{"numeroControlePNCP": "x" + params["dataInicial"], "orgaoEntidade": {"esferaId": "M"}}],
                    "paginasRestantes": 0}

    diretas, completas = p.compras_diretas(Metade(), d(2025, 1, 1), d(2025, 1, 14), minutos=5)
    assert completas is False and set(diretas) == {"x20250108"}


def test_semanas_divididas_entre_partes():
    todas = list(pncp._janelas(date(2025, 1, 1), date(2025, 12, 31)))
    partes = [pncp._semanas(date(2025, 1, 1), date(2025, 12, 31), i, 4) for i in range(4)]
    assert sorted(j for p in partes for j in p) == sorted(todas)
    assert partes[1][0] == todas[1]


class _PorConsulta:
    """Contratos por semana: só a semana de 2025-01-08 tem um contrato municipal e um estadual."""

    def get_json(self, url, params=None):
        if "/itens" in url or "contratacoes" in url:
            return [] if "/itens" in url else {"data": [], "paginasRestantes": 0}
        if params["dataInicial"] == "20250108":
            return {"data": [_contrato(1), _contrato(2, esfera="E")], "paginasRestantes": 0}
        return {"data": [], "paginasRestantes": 0}


def test_partes_e_juntar(tmp_path):
    pasta = tmp_path / "partes"
    hoje = date(2025, 1, 20)
    assert pncp.baixar_parte(_PorConsulta(), pasta, [2025], 0, 2, hoje=hoje) == 0
    assert pncp.baixar_parte(_PorConsulta(), pasta, [2025], 1, 2, hoje=hoje) == 1
    saida = tmp_path / "site"
    assert pncp.juntar(_PorConsulta(), pasta, saida, [2025], hoje=hoje) == 1
    doc = md.ler((saida / "v1/municipios/sc/4208203/2025-contratos.md").read_text(encoding="utf-8"))
    assert doc.tabelas["contratos"][0]["empresa"] == "EMPRESA"
    import json

    marca = json.loads((saida / pncp.MARCA.format(ano=2025)).read_text())
    assert marca["contratos_completos"] and marca["diretas_completas"] and marca["partes"] == 2


def test_juntar_com_parte_faltando_marca_incompleto(tmp_path):
    pasta = tmp_path / "partes"
    hoje = date(2025, 1, 20)
    pncp.baixar_parte(_PorConsulta(), pasta, [2025], 1, 2, hoje=hoje)
    saida = tmp_path / "site"
    assert pncp.juntar(_PorConsulta(), pasta, saida, [2025], hoje=hoje) == 1
    texto = (saida / "v1/municipios/sc/4208203/2025-contratos.md").read_text(encoding="utf-8")
    assert "contratacoes-diretas" in texto and "incompleta" in texto
