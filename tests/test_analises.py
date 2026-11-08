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


def test_centro_governista_nao_vira_esquerda():
    """Votações governo x oposição em que o centro vota com a esquerda não
    contam se a direita de referência também se divide igual ao centro."""
    votos = []
    for j in range(30):
        # consenso governo + centro + direita: não é ideológica
        for cod, partido in [(1, "PT"), (2, "PT"), (3, "PT"), (10, "PSD"), (11, "PSD"), (20, "PL"), (21, "PL"), (22, "PL")]:
            votos.append(VotoSimples(f"c{j}", cod, partido, "sim"))
    r = espectro.calcular(votos)
    assert r.votacoes == {} and r.pct_esquerda == {}


def test_poucos_dados_nao_quebra():
    r = espectro.calcular([VotoSimples("a", 1, "PT", "sim")])
    assert r.pct_esquerda == {}


def test_motivo_atencao():
    assert motivo_atencao("Fixa o subsídio dos membros do Congresso Nacional.") is not None
    assert motivo_atencao("Altera o Fundo Especial de Financiamento de Campanha.") is not None
    assert motivo_atencao("Dispõe sobre emendas de relator ao orçamento.") is not None
    assert motivo_atencao("Institui o dia nacional do café.") is None
    assert motivo_atencao(None) is None


def test_alinhamento_nao_conta_o_proprio_voto():
    """Num partido de uma pessoa, o alinhamento com ele não pode ser 100% só
    porque a maioria do partido é ela mesma."""
    votos = []
    for j in range(20):
        votos.append(VotoSimples(f"v{j}", 1, "SOLO", "sim" if j % 2 else "nao"))
        for cod in range(10, 14):
            votos.append(VotoSimples(f"v{j}", cod, "PX", "sim"))
    alinh = espectro.alinhamento_partidos(votos)
    assert "SOLO" not in {a["partido"] for a in alinh[1]}
    px = next(a for a in alinh[1] if a["partido"] == "PX")
    assert px["pct"] == 50.0 and px["votacoes"] == 20


def test_calcular_com_lados_dados_so_recalcula_percentual():
    votos = _simular()
    tudo = espectro.calcular(votos)
    metade = [v for v in votos if int(v.votacao_id[1:].split(":")[0]) < 30]
    r = espectro.calcular(metade, lados=tudo.votacoes)
    assert set(r.votacoes) <= {v.votacao_id for v in metade}
    assert all(r.votacoes[vid] is tudo.votacoes[vid] for vid in r.votacoes)
    assert r.pct_esquerda[0][1] < tudo.pct_esquerda[0][1]
