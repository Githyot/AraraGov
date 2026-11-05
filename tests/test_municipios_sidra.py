from datetime import date
from decimal import Decimal as D

from araragov.municipios import md, referencias, sidra
from araragov.collectors.referencia import IPCA_URL

CAB = {"NC": "Nível Territorial (Código)", "NN": "Nível Territorial", "MC": "Unidade de Medida (Código)",
       "MN": "Unidade de Medida", "V": "Valor", "D1C": "Unidade da Federação (Código)",
       "D1N": "Unidade da Federação", "D2C": "Variável (Código)", "D2N": "Variável",
       "D3C": "Mês (Código)", "D3N": "Mês"}


def _l(uf, mes, v):
    return {"NC": "3", "D1C": uf, "D2C": "48", "D3C": mes, "V": v}


SIDRA = [CAB, _l("41", "202301", "1700.00"), _l("41", "202306", "1750.00"), _l("41", "202312", "1800.00"),
         _l("41", "202501", "1900.00"), _l("42", "202306", "1800.50"), _l("41", "202307", "...")]


class Cliente:
    def get_json(self, url, params=None):
        if url == sidra.URL:
            return SIDRA
        if url == IPCA_URL:
            return [{"data": f"01/{m:02d}/{a}", "valor": "0.5"} for a in range(2018, 2027) for m in range(1, 13)]
        raise AssertionError(url)


def test_custo_medio_indices_e_observacoes():
    mensal = sidra.custo_medio(Cliente())
    assert mensal[("PR", "2023-06")] == D("1750.00") and ("PR", "2023-07") not in mensal
    assert sidra.indices_anuais(mensal)[("PR", 2023)] == D("1750.00")
    obs = {(o.uf, o.ano): o for o in sidra.observacoes(mensal)}
    assert obs[("PR", 2023)].competencia == "2023-06" and obs[("PR", 2025)].competencia == "2025-01"
    assert obs[("SC", 2023)].item == "edificacao-media"


def test_gerar_arquivo_por_estado(tmp_path):
    referencias.gerar(Cliente(), tmp_path, ["PR"], [2023, 2024], hoje=date(2026, 11, 5))
    doc = md.ler((tmp_path / "v1/referencia/custos/pr.md").read_text(encoding="utf-8"))
    refs = {(r["item"], r["ano"]): r for r in doc.tabelas["referencias"]}
    assert refs[("edificacao-media", "2023")]["nivel"] == "1"
    # 2024 sem dado nem índice no PR: vem de 2023 corrigido pelo IPCA, com aviso
    r = refs[("edificacao-media", "2024")]
    assert r["nivel"] == "3" and "IPCA" in r["metodo"] and "IPCA" in r["avisos"]
