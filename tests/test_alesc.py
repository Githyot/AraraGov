from pathlib import Path

from sqlalchemy import select

from araragov import db
from araragov.collectors import alesc
from araragov.collectors._comum import casar_nome

FIX = Path(__file__).parent / "fixtures"

CANDIDATOS = {
    1: ["Paulinha", "Ana Paula da Silva"],
    2: ["Dr. Vicente Caropreso", "Vicente Augusto Caropreso"],
    3: ["Marcos da Rosa", "Marcos da Rosa"],
    4: ["Marcos Vieira", "Marcos Luiz Vieira"],
    5: ["Alex Brasil", "Alexander Brasil Alves Pereira"],
}


def test_casar_nome_como_a_assembleia_escreve():
    assert casar_nome("Ana Paula da Silva (Paulinha)", CANDIDATOS) == 1
    assert casar_nome("Vicente Caropreso", CANDIDATOS) == 2
    assert casar_nome("Marcos Luiz Vieira", CANDIDATOS) == 4
    assert casar_nome("Marcos da Rosa", CANDIDATOS) == 3
    assert casar_nome("Alex Brasil", CANDIDATOS) == 5
    assert casar_nome("Rodrigo Minotto ", CANDIDATOS) is None


def test_casar_nome_ambiguo_fica_sem_dono():
    assert casar_nome("Marcos", CANDIDATOS) is None
    assert casar_nome("João Silva", {1: ["João Silva Souza"], 2: ["João Pedro Silva"]}) is None


def test_gastos_de_gabinete_alesc(client):
    with db.sessao() as s:
        for cod, (nome, civil) in CANDIDATOS.items():
            s.add(db.Politico(casa="al-sc", cargo="Deputado estadual", codigo=cod, nome=nome, nome_civil=civil, uf="SC"))
    client.bytes(alesc.GABINETES.format(ano=2025), (FIX / "alesc_gabinetes_2025.csv").read_bytes())
    assert alesc.coletar_despesas(client, 2025) == 4
    with db.sessao() as s:
        ds = s.execute(select(db.Despesa).order_by(db.Despesa.valor)).scalars().all()
    assert [(d.codigo_politico, float(d.valor), d.mes) for d in ds] == [(None, 99.9, 5), (2, 1018.8, 10), (2, 1018.8, 10), (1, 3500.0, 1)]
    assert ds[-1].fornecedor == "Imóveis Planeta Ltda" and ds[-1].categoria == "Escritório de Apoio - Aluguel"
