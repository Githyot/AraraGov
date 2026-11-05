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
    assert casar_nome("ALEX BRASIL", {9: ["Alexander Brasil Alves Pereira", None]}) == 9
    assert casar_nome("LUNELLI", {7: ["Antidio Aleixo Lunelli", None], 8: ["Ana Paula Silva", None]}) == 7
    assert casar_nome("SILVA", {7: ["Joao Silva", None], 8: ["Ana Silva", None]}) is None


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


LISTA_ALESC = """<tbody>
<tr><td class="fw-semibold">PAULINHA</td><td class="text-center">10/2026</td><td class="text-end">
<a href="/deputados/contracheque/9386?ano=2026&amp;mes=10" hx-get="/deputados/contracheque/9386?ano=2026&amp;mes=10">Remuneração</a></td></tr>
<tr><td class="fw-semibold">DR VICENTE CAROPRESO</td><td>10/2026</td><td>
<a href="/deputados/contracheque/7726?ano=2026&amp;mes=10">Remuneração</a></td></tr>
<tr><td class="fw-semibold">EMERSON STEIN</td><td>10/2026</td><td>
<a href="/deputados/contracheque/12001?ano=2026&amp;mes=10">Remuneração</a></td></tr>
</tbody>"""


def test_lista_oficial_da_alesc_traz_suplente_e_tira_quem_saiu(client, monkeypatch):
    with db.sessao() as s:
        for cod, (nome, civil) in CANDIDATOS.items():
            s.add(db.Politico(casa="al-sc", cargo="Deputado estadual", codigo=cod, nome=nome, nome_civil=civil, uf="SC", partido="X", fonte="tse", em_exercicio=True))
    assert alesc.ler_deputados(LISTA_ALESC) == [
        {"id": 9386, "nome": "PAULINHA"}, {"id": 7726, "nome": "DR VICENTE CAROPRESO"}, {"id": 12001, "nome": "EMERSON STEIN"}
    ]
    client.bytes(alesc.DEPUTADOS, LISTA_ALESC.encode())
    monkeypatch.setattr(alesc, "ler_deputados", lambda html, f=alesc.ler_deputados: f(html) * 12)  # passa do mínimo de 30
    assert alesc.coletar_deputados(client) == 3
    with db.sessao() as s:
        ps = {p.codigo: p for p in s.execute(select(db.Politico).where(db.Politico.casa == "al-sc")).scalars()}
    assert ps[1].em_exercicio and ps[1].fonte == "tse-assembleia"
    assert ps[2].em_exercicio
    assert not ps[3].em_exercicio and not ps[5].em_exercicio
    sup = ps[1_000_000 + 12001]
    assert (sup.nome, sup.fonte, sup.em_exercicio, sup.partido) == ("Emerson Stein", "assembleia", True, None)


SERVIDORES_P1 = """<select id="setor-id" name="setor_id"><option value="">Todos</option>
<option value="2227">COP - GERENCIA DO SISTEMA DE CONTROLE DO ORCAMENTO DE GABINETE</option>
<option value="9386">GAB DEP PAULINHA</option>
<option value="7">GAB DEP NINGUEM CONHECIDO</option></select>
<table><tr><td class="fw-semibold">ABEL VEIGA</td> <td>Comissionado</td> <td class="small">DG - DIRETORIA</td></tr></table>
Página 1 de 133, exibindo 20 de 2.641 registros."""
GAB_P1 = """<tr><td class="fw-semibold">MARIA DA SILVA</td>
<td>Comissionado</td>
<td class="small">GAB DEP PAULINHA</td></tr> Página 1 de 2, exibindo 20"""
GAB_P2 = """<tr><td class="fw-semibold">JOSE SOUZA</td><td>Efetivo</td><td class="small">GAB DEP PAULINHA</td></tr> Página 2 de 2"""


def test_gabinetes_alesc(client):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-sc", cargo="Deputado estadual", codigo=1, nome="Paulinha", nome_civil="Ana Paula da Silva", uf="SC"))
    assert alesc.ler_setores_gabinete(SERVIDORES_P1) == {9386: "PAULINHA", 7: "NINGUEM CONHECIDO"}
    client.bytes(alesc.SERVIDORES, SERVIDORES_P1.encode())
    client.bytes(f"{alesc.SERVIDORES}?setor_id=9386&page=1", GAB_P1.encode())
    client.bytes(f"{alesc.SERVIDORES}?setor_id=9386&page=2", GAB_P2.encode())
    assert alesc.coletar_gabinetes(client) == 2
    with db.sessao() as s:
        equipe = s.execute(select(db.Assessor).order_by(db.Assessor.nome)).scalars().all()
    assert [(a.codigo_politico, a.nome, a.cargo, a.remuneracao) for a in equipe] == [
        (1, "Jose Souza", "Efetivo", None), (1, "Maria da Silva", "Comissionado", None)
    ]
