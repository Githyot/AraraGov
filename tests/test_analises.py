import random

from araragov.analise import espectro
from araragov.analise.atencao import motivo_atencao
from araragov.analise.espectro import VotoSimples


def _simular(n_votacoes=60, seed=1):
    """Dois blocos ideológicos com ruído: PT/PSOL (esquerda) e PL/NOVO (direita),
    mais um bloco de centro (PSD) que se divide."""
    rnd = random.Random(seed)
    politicos = (
        [(i, "PT", -1.0) for i in range(20)]
        + [(100 + i, "PSOL", -1.3) for i in range(6)]
        + [(200 + i, "PSD", 0.0) for i in range(15)]
        + [(300 + i, "PL", 1.0) for i in range(20)]
        + [(400 + i, "NOVO", 1.2) for i in range(5)]
    )
    votos = []
    for j in range(n_votacoes):
        direcao = rnd.choice([-1, 1])  # se "sim" é a posição da esquerda ou da direita
        for cod, partido, ideologia in politicos:
            prob_sim = 0.5 + 0.45 * direcao * -ideologia / 1.3
            prob_sim = min(max(prob_sim, 0.03), 0.97)
            voto = "sim" if rnd.random() < prob_sim else "nao"
            votos.append(VotoSimples(f"v{j}:{direcao}", cod, partido, voto))
    return votos


def test_espectro_separa_blocos_e_orienta_pela_referencia():
    r = espectro.calcular(_simular())
    assert r.pct_esquerda[0][0] > 75  # PT
    assert r.pct_esquerda[100][0] > 75  # PSOL
    assert r.pct_esquerda[300][0] < 25  # PL
    assert 30 < r.pct_esquerda[200][0] < 70  # PSD no meio
    assert r.pontuacao[0] < 0 < r.pontuacao[300]


def test_classifica_lado_das_votacoes():
    r = espectro.calcular(_simular())
    acertos = 0
    for vid, lado in r.votacoes.items():
        direcao = int(vid.split(":")[1])
        esperado = "esquerda" if direcao == 1 else "direita"
        acertos += lado.lado_sim == esperado
    assert acertos / len(r.votacoes) > 0.9


def test_faixas_sem_rotulos_extremos():
    assert {espectro.faixa(p) for p in range(0, 101, 5)} == {
        "esquerda", "centro-esquerda", "centro", "centro-direita", "direita"
    }


def test_alinhamento_partidos():
    alinh = espectro.alinhamento_partidos(_simular())
    pt = {a["partido"]: a["pct"] for a in alinh[0]}
    assert pt["PT"] > pt["PL"]
    assert alinh[0][0]["partido"] in {"PT", "PSOL"}


def test_poucos_dados_nao_quebra():
    r = espectro.calcular([VotoSimples("a", 1, "PT", "sim")])
    assert r.pct_esquerda == {}


def test_motivo_atencao():
    assert motivo_atencao("Fixa o subsídio dos membros do Congresso Nacional.") is not None
    assert motivo_atencao("Altera o Fundo Especial de Financiamento de Campanha.") is not None
    assert motivo_atencao("Dispõe sobre emendas de relator ao orçamento.") is not None
    assert motivo_atencao("Institui o dia nacional do café.") is None
    assert motivo_atencao(None) is None
