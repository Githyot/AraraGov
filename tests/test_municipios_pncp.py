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
