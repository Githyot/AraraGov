from datetime import date

from araragov.municipios import md, tcerj

R = {"Ente": "MACAE", "UnidadeGestora": "26", "NumeroContrato": "00/2024", "AnoContrato": 2024,
     "CNPJCPFContratado": "12595412000109", "Contratado": "J CARNEIRO LOCACAO LTDA",
     "ProcessoLicitatorio": "0416/2023", "Modalidade": "PREGÃO PRESENCIAL", "ProcessoDispensa": None,
     "Objeto": "PAVIMENTAÇÃO ASFÁLTICA DA RUA A", "DataAssinaturaContrato": "2024-04-08",
     "ValorContrato": 1582937.0, "ValorPago": 100.5}
PF = dict(R, NumeroContrato="001/2024", CNPJCPFContratado="**********", Contratado="DOUGLAS", ProcessoLicitatorio=None,
          Modalidade=None, ProcessoDispensa="16245/2024", Objeto="APOIO CULTURAL", ValorContrato=20000.0)
D = [dict(R, NumeroContrato=f"D{i}", ProcessoLicitatorio=None, Modalidade=None, ProcessoDispensa=f"{i}/2024",
          Objeto="MATERIAL DE LIMPEZA", ValorContrato=1000.0) for i in range(3)]


class C:
    def get_json(self, url, params):
        assert url.endswith("/contratos_municipio")
        if params["municipio"] == "MACAE":
            return {"Contratos": [R, R, PF] + D, "Count": 6}
        return {"Contratos": [], "Count": 0}


def test_gerar_rj(tmp_path):
    assert tcerj.gerar(C(), tmp_path, [2024], hoje=date(2026, 11, 5)) == 1
    texto = (tmp_path / "v1/municipios/rj/3302403/2024-contratos.md").read_text(encoding="utf-8")
    doc = md.ler(texto)
    assert doc.meta["uf"] == "RJ"
    c = doc.tabelas["contratos"]
    assert len(c) == 5 and c[0]["cnpj"] == "12.595.412/0001-09" and str(c[0]["pago"]) == "100.5"
    assert "DOUGLAS" not in texto
    assert doc.tabelas["obras"][0]["comparacao"] == "Quantidade não informada no contrato"
    assert doc.tabelas["contratacoes-diretas"][0]["contratacoes"] == "3"
    assert doc.tabelas["sem-dados"][0]["responsavel"] == "Prefeitura"
