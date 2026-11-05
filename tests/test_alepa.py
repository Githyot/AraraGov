from pathlib import Path

import pytest
from sqlalchemy import select

from araragov import db
from araragov.collectors import alepa

FIX = Path(__file__).parent / "fixtures"


def test_ler_gabinetes_alepa():
    g = alepa.ler_gabinetes((FIX / "alepa_gabinetes.html").read_text())
    assert [x["deputado"] for x in g] == ["ADRIANO COELHO", "NINGUEM CONHECIDO"]
    assert g[0]["referencia"] == "2026-10" and g[0]["assessores"] == 2 and float(g[0]["total"]) == 5379.7
    assert g[0]["detalhe"] == alepa.BASE + "frame_verbadetalhe.php?mes=M1lP&ano=UURP&gab=TlJW&tipo=RjYx"


def test_equipe_dos_gabinetes_alepa(client, monkeypatch):
    with db.sessao() as s:
        s.add(db.Politico(casa="al-pa", cargo="Deputado estadual", codigo=3, nome="Adriano Coelho", nome_civil="Adriano Coelho da Silva", uf="PA"))
    pagina = (FIX / "alepa_gabinetes.html").read_text()
    client.bytes(alepa.GABINETES, pagina.encode())
    client.bytes(alepa.BASE + "frame_verbadetalhe.php?mes=M1lP&ano=UURP&gab=TlJW&tipo=RjYx", (FIX / "alepa_detalhe.html").read_bytes())
    with pytest.raises(RuntimeError):
        alepa.coletar_gabinetes(client)  # só 2 gabinetes: página incompleta
    monkeypatch.setattr(alepa, "ler_gabinetes", lambda p, f=alepa.ler_gabinetes: f(p) + [dict(f(p)[1], deputado=f"OUTRO {i}") for i in range(20)])
    assert alepa.coletar_gabinetes(client) == 2
    with db.sessao() as s:
        a = s.execute(select(db.Assessor).order_by(db.Assessor.remuneracao)).scalars().all()
    assert [(x.codigo_politico, x.nome, float(x.remuneracao), x.remuneracao_ref) for x in a] == [
        (3, "Adalto Paixao Lima Azevedo", 1621.0, "2026-10"), (3, "Adriana Silva dos Santos", 3758.7, "2026-10")]
