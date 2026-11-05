from araragov import cli


def _falhar(*_):
    raise RuntimeError("fora do ar")


def test_fonte_com_reserva_nao_falha_a_coleta(monkeypatch):
    monkeypatch.setitem(cli.ALVOS, "almg-deputados", _falhar)
    assert cli.main(["coletar", "almg-deputados"]) == 0


def test_fonte_principal_falha_a_coleta(monkeypatch):
    monkeypatch.setitem(cli.ALVOS, "camara-deputados", _falhar)
    assert cli.main(["coletar", "camara-deputados"]) == 1


def test_anos_por_alvo():
    from araragov.cli import _anos_do_alvo

    anos = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    assert _anos_do_alvo("camara-votacoes", anos) == anos
    assert _anos_do_alvo("camara-recursos", anos) == [2025, 2026]
    assert _anos_do_alvo("camara-deputados", anos) == [2026]
