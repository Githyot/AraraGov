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


def perfil(i, nome):
    casa = "senado" if i % 4 == 0 else "camara"
    resumo = {
        "id": f"{casa}-{9000 + i}", "casa": casa,
        "cargo": "Senador" if casa == "senado" else "Deputado Federal",
        "nome": nome, "partido": PARTIDOS[i % len(PARTIDOS)], "uf": UFS[i % len(UFS)],
        "foto": None, "em_exercicio": i != 9,
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
        "gabinete": [{"nome": f"Assessor Exemplo {k}", "cargo": "Secretário Parlamentar", "nivel": f"SP{10 + k}", "desde": "2023-02-01"} for k in range(1, 13)],
        "presenca": {v: votos.count(v) for v in set(votos)},
        "votacoes": [
            {"id": f"exemplo:{k}", "data": f"2025-{12 - k % 12:02d}-10T18:00:00", "proposicao": pr, "descricao": None,
             "ementa": em, "resultado": "Aprovada" if k % 3 else "Rejeitada", "link": None, "voto": votos[k],
             "partido_na_epoca": resumo["partido"]}
            for k, (pr, em) in enumerate(VOTACOES)
        ],
    }
    return resumo, p


os.makedirs(os.path.join(SAIDA, "politicos"), exist_ok=True)
lista = []
for i, nome in enumerate(NOMES):
    resumo, p = perfil(i, nome)
    lista.append(resumo)
    with open(os.path.join(SAIDA, "politicos", f"{resumo['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False)
with open(os.path.join(SAIDA, "politicos.json"), "w", encoding="utf-8") as f:
    json.dump(lista, f, ensure_ascii=False)
print(len(lista), "perfis de exemplo em", SAIDA)
