#!/usr/bin/env python3
"""Gera dados de EXEMPLO, com políticos fictícios, para desenvolver o app
sem internet (flutter run --dart-define=ARARAGOV_AMOSTRA=true).

Nenhum nome ou número aqui corresponde a uma pessoa real.
"""
import json
import os
import random

random.seed(7)
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "amostra", "v1")
PARTIDOS = ["PEX", "PFI", "PAM", "PDE", "PTO"]
UFS = ["SP", "RJ", "MG", "BA", "RS", "PE", "CE", "PA", "AM", "DF"]
NOMES = ["Ana Exemplo", "Bruno Fictício", "Carla Modelo", "Diego Amostra", "Elisa Teste",
         "Fábio Ilustrativo", "Gabriela Demo", "Hugo Protótipo", "Iara Simulada", "João Hipotético"]
CATEGORIAS = ["Passagens aéreas", "Divulgação da atividade parlamentar", "Manutenção de escritório",
              "Combustíveis e lubrificantes", "Telefonia", "Locação de veículos"]
SALARIO = [
    {"desde": "2015-02-01", "valor": 33763.0, "ato": "Decreto Legislativo 276/2014", "fonte": None},
    {"desde": "2023-01-01", "valor": 39293.32, "ato": "Decreto Legislativo 172/2022", "fonte": None},
    {"desde": "2023-04-01", "valor": 41650.92, "ato": "Decreto Legislativo 172/2022", "fonte": None},
    {"desde": "2024-02-01", "valor": 44008.52, "ato": "Decreto Legislativo 172/2022", "fonte": None},
    {"desde": "2025-02-01", "valor": 46366.19, "ato": "Decreto Legislativo 172/2022", "fonte": None},
]
VOTACOES = [(f"PL {100 + i}/2025", f"Projeto de lei fictício número {i + 1} (exemplo).") for i in range(14)]


def faixa(p):
    return "esquerda" if p >= 65 else "centro-esquerda" if p >= 55 else "centro" if p > 45 else "centro-direita" if p > 35 else "direita"


def perfil(i, nome):
    pe = round(15 + (i * 37) % 70, 1)
    pe_partido = round(min(max(pe + random.uniform(-8, 8), 0), 100), 1)
    casa = "senado" if i % 4 == 0 else "camara"
    resumo = {
        "id": f"{casa}-{9000 + i}", "casa": casa,
        "cargo": "Senador" if casa == "senado" else "Deputado Federal",
        "nome": nome, "partido": PARTIDOS[i % len(PARTIDOS)], "uf": UFS[i % len(UFS)],
        "foto": None, "em_exercicio": i != 9, "doa_salario": i == 1,
    }
    anos = [{"ano": a, "valor": round(random.uniform(250e3, 520e3), 2)} for a in (2023, 2024, 2025)]
    votos = random.choices(["sim", "nao", "abstencao", "ausente", "obstrucao"], weights=[50, 30, 4, 12, 4], k=len(VOTACOES))
    p = {
        **resumo,
        "nome_civil": nome + " da Silva",
        "email": None,
        "salario": {
            "atual": 46366.19, "historico": SALARIO,
            "vs_inflacao": {"desde": "2015-02-01", "valor_inicial": 33763.0, "valor_atual": 46366.19,
                            "corrigido_pela_inflacao": 57210.4, "acima_da_inflacao_pct": -18.95},
        },
        "gastos": {
            "total": sum(a["valor"] for a in anos), "por_ano": anos, "por_mes": [],
            "anos": {str(a["ano"]): {"total": a["valor"],
                                     "por_categoria": [{"nome": CATEGORIAS[0], "valor": round(a["valor"] * 0.6, 2)}, {"nome": CATEGORIAS[1], "valor": round(a["valor"] * 0.4, 2)}],
                                     "maiores_fornecedores": [{"nome": f"Fornecedor Exemplo {a['ano']} Ltda", "valor": round(a["valor"] * 0.2, 2)}]}
                     for a in anos},
            "por_categoria": sorted(({"nome": c, "valor": round(random.uniform(5e3, 300e3), 2)} for c in CATEGORIAS), key=lambda x: -x["valor"]),
            "maiores_fornecedores": [{"nome": f"Fornecedor Exemplo {k} Ltda", "valor": round(random.uniform(5e3, 90e3), 2)} for k in range(1, 6)],
            "vs_inflacao": [
                {"ano": a["ano"], "desde": "2023-12-01", "valor_inicial": anos[0]["valor"], "valor": a["valor"],
                 "corrigido_pela_inflacao": round(anos[0]["valor"] * (1.045 ** (a["ano"] - 2023)), 2),
                 "acima_da_inflacao_pct": round((a["valor"] / (anos[0]["valor"] * 1.045 ** (a["ano"] - 2023)) - 1) * 100, 2)}
                for a in anos[1:]
            ],
            "documentos_recentes": [
                {"data": f"2025-{m:02d}-15", "categoria": random.choice(CATEGORIAS),
                 "fornecedor": f"Fornecedor Exemplo {m} Ltda", "valor": round(random.uniform(300, 12e3), 2), "url": None}
                for m in range(10, 0, -1)
            ],
        },
        "gabinete": [{"nome": f"Assessor Exemplo {k}", "cargo": "Secretário Parlamentar", "nivel": f"SP{10 + k}", "desde": "2023-02-01", "remuneracao": 3000 + 500 * k, "remuneracao_ref": "2026-09"} for k in range(1, 13)],
        "custo_gabinete": {"mensal": sum(3000 + 500 * k for k in range(1, 13)), "pessoas_com_valor": 12, "pessoas": 12, "referencia": "2026-09"},
        "emendas": {"total_empenhado": 18_500_000, "total_pago": 11_200_000, "quantidade": 24,
                    "por_ano": [{"ano": 2023, "empenhado": 6_000_000, "pago": 5_000_000}, {"ano": 2024, "empenhado": 6_500_000, "pago": 4_200_000}, {"ano": 2025, "empenhado": 6_000_000, "pago": 2_000_000}],
                    "por_area": [{"nome": "Saúde", "valor": 9_000_000}, {"nome": "Urbanismo", "valor": 5_500_000}, {"nome": "Educação", "valor": 4_000_000}],
                    "por_local": [{"nome": "Cidade Exemplo - EX", "valor": 7_000_000}, {"nome": "Vila Fictícia - EX", "valor": 4_000_000}],
                    "favorecidos": [{"nome": "Prefeitura de Cidade Exemplo", "documento": None, "tipo": "Pessoa Jurídica", "municipio": "Cidade Exemplo", "uf": "EX", "valor": 6_000_000}],
                    "anos": {str(a): {"total_empenhado": e, "total_pago": pg, "quantidade": 8, "por_area": [{"nome": "Saúde", "valor": e}], "por_local": [], "favorecidos": []}
                             for a, e, pg in ((2023, 6_000_000, 5_000_000), (2024, 6_500_000, 4_200_000), (2025, 6_000_000, 2_000_000))}},
        "verba_gabinete": None if casa == "senado" else {
            "total": 12 * 120000.0, "por_ano": [{"ano": 2025, "valor": 12 * 120000.0}],
            "anos": {"2025": {"total": 12 * 120000.0, "por_mes": [{"mes": m, "valor": 120000.0} for m in range(1, 13)]}}},
        "salario_pago": None if casa == "senado" else {
            "total": 44008.52 + 11 * 46366.19, "por_ano": [{"ano": 2025, "valor": 44008.52 + 11 * 46366.19}],
            "anos": {"2025": {"total": 44008.52 + 11 * 46366.19, "por_mes": [{"mes": m, "valor": 44008.52 if m == 1 else 46366.19} for m in range(1, 13)]}}},
        "doacao_salario": {"parte": "20%", "descricao": "Declara doar parte do salário a instituições (exemplo).", "fonte": "https://example.org/declaracao", "data": "2025-01-10"} if i == 1 else None,
        "beneficios": [{"tipo": "imovel_funcional", "descricao": "Ocupa imóvel funcional em Brasília", "valor_mensal": None, "referencia": "04/11/2026", "fonte": None}]
                      + ([] if casa == "senado" else [{"tipo": "auxilio_moradia", "descricao": "Recebeu auxílio-moradia", "valor_mensal": None, "valor_ano": 29771.0, "ano": 2025, "referencia": "2025", "fonte": None}]),
        "presenca": {v: votos.count(v) for v in set(votos)},
        "posicao": {"pct_esquerda": pe, "pct_direita": round(100 - pe, 1), "faixa": faixa(pe),
                    "votacoes_consideradas": 180, "media_do_partido": pe_partido, "faixa_do_partido": faixa(pe_partido)},
        "alinhamento": {
            "mais_alinhados": [{"partido": PARTIDOS[(i + k) % 5], "pct": round(92 - 9 * k, 1), "votacoes": 180 - k} for k in range(5)],
            "menos_alinhados": [],
            "proprio_partido": {"partido": PARTIDOS[i % 5], "pct": 92.0, "votacoes": 180},
        },
        "atencao": {"votacoes": 2, "votou_sim": 1, "votou_nao": 1},
        "votacoes": [
            {"id": f"exemplo:{k}", "data": f"2025-{12 - k % 12:02d}-10T18:00:00", "proposicao": pr, "descricao": None,
             "ementa": em, "resultado": "Aprovada" if k % 3 else "Rejeitada", "link": None, "voto": votos[k],
             "partido_na_epoca": resumo["partido"],
             "lado_sim": None if k % 4 == 3 else ("esquerda" if k % 2 else "direita"),
             "atencao": "Trata de fundo eleitoral ou partidário (exemplo)" if k in (1, 6) else None}
            for k, (pr, em) in enumerate(VOTACOES)
        ],
    }
    # Mesmo formato da API real: todos os votos compactos, detalhes inline só
    # dos 8 mais recentes e dos de atenção; o resto em votacoes/{ano}.json.
    completos = sorted(p["votacoes"], key=lambda v: v["data"], reverse=True)
    p["votos_formato"] = ["id", "data", "voto", "lado_sim", "atencao"]
    p["votos"] = [[v["id"], v["data"][:10], v["voto"], v["lado_sim"], 1 if v["atencao"] else 0] for v in completos]
    p["votacoes"] = [v for i, v in enumerate(completos) if i < 8 or v["atencao"]]
    for v in completos:
        DETALHES[v["id"]] = {k: v[k] for k in ("data", "proposicao", "descricao", "ementa", "resultado", "link", "lado_sim", "atencao")}
    return resumo, p


DETALHES = {}


os.makedirs(os.path.join(SAIDA, "politicos"), exist_ok=True)
lista = []
for i, nome in enumerate(NOMES):
    resumo, p = perfil(i, nome)
    lista.append(resumo)
    with open(os.path.join(SAIDA, "politicos", f"{resumo['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False)
os.makedirs(os.path.join(SAIDA, "votacoes"), exist_ok=True)
with open(os.path.join(SAIDA, "votacoes", "2025.json"), "w", encoding="utf-8") as f:
    json.dump(DETALHES, f, ensure_ascii=False)
with open(os.path.join(SAIDA, "politicos.json"), "w", encoding="utf-8") as f:
    json.dump(lista, f, ensure_ascii=False)
print(len(lista), "perfis de exemplo em", SAIDA)
