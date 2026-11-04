from sqlalchemy import select

from araragov import db
from araragov.collectors import beneficios, senado

CSV = (
    "ÚLTIMA ATUALIZAÇÃO;04/11/2026 05:00\n"
    "NOME;ESTADO;PARTIDO;AUXÍLIO-MORADIA;IMÓVEL FUNCIONAL\n"
    "CONFÚCIO MOURA;RO;MDB;NÃO;SIM\n"
    "SENADORA EXEMPLO;BA;PT;SIM;NÃO\n"
    "NINGUÉM CADASTRADO;SP;PL;SIM;NÃO\n"
).encode("latin-1")


def test_moradia_senado(client):
    client.json(f"{senado.API}/senador/lista/atual", "senado_lista_atual.json")
    senado.coletar_senadores(client)
    client.bytes(beneficios.SENADO_MORADIA_URL, CSV)
    assert beneficios.coletar_moradia_senado(client) == 2
    with db.sessao() as s:
        bs = {(b.codigo_politico, b.tipo): b for b in s.execute(select(db.Beneficio)).scalars()}
    assert set(bs) == {(475, "imovel_funcional"), (5000, "auxilio_moradia")}
    assert bs[(475, "imovel_funcional")].referencia == "04/11/2026"
