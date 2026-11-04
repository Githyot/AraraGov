from araragov import cli


def _falhar(*_):
    raise RuntimeError("fora do ar")


def test_fonte_com_reserva_nao_falha_a_coleta(monkeypatch):
    monkeypatch.setitem(cli.ALVOS, "almg-deputados", _falhar)
    assert cli.main(["coletar", "almg-deputados"]) == 0


def test_fonte_principal_falha_a_coleta(monkeypatch):
    monkeypatch.setitem(cli.ALVOS, "camara-deputados", _falhar)
    assert cli.main(["coletar", "camara-deputados"]) == 1
