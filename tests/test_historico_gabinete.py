import json
from datetime import date

from araragov import db
from araragov.collectors import historico
from araragov.exportar import exportar


def _coleta(client, tmp_path, pessoas, anterior=None):
    """Simula uma coleta: banco novo, histórico da publicação anterior, equipe de hoje."""
    db.configurar("sqlite://")
    if anterior is not None:
        client.rotas.clear()
        client.bytes(f"https://exemplo/v1/{historico.ARQUIVO}", anterior)
        client.get_json = lambda u, p=None: json.loads(client.get_bytes(u, p))
        historico.carregar(client, "https://exemplo/v1")
    with db.sessao() as s:
        s.add(db.Politico(casa="camara", cargo="Deputado Federal", codigo=1, nome="Deputada A", uf="SP"))
        for nome in pessoas:
            s.add(db.Assessor(casa="camara", codigo_politico=1, nome=nome, cargo="Secretário Parlamentar",
                              funcao="SP10C", desde=date(2025, 3, 1)))
    exportar(tmp_path)
    perfil = json.loads((tmp_path / "v1/politicos/camara-1.json").read_text())
    return perfil, (tmp_path / "v1/historico/recursos.json").read_bytes()


def test_quem_sai_do_gabinete_vira_ex_membro(client, tmp_path):
    perfil, publicado = _coleta(client, tmp_path, ["MARIA SILVA", "JOSÉ SOUZA"])
    assert perfil["gabinete_anteriores"] == []

    perfil, publicado = _coleta(client, tmp_path, ["MARIA SILVA"], publicado)
    assert [g["nome"] for g in perfil["gabinete"]] == ["MARIA SILVA"]
    (ex,) = perfil["gabinete_anteriores"]
    assert ex["nome"] == "JOSÉ SOUZA" and ex["desde"] == "2025-03-01" and ex["ate"] == date.today().isoformat()

    # Fonte da Câmara fora do ar: ninguém "sai" e o ex-membro continua guardado.
    perfil, publicado = _coleta(client, tmp_path, [], publicado)
    assert [g["nome"] for g in perfil["gabinete_anteriores"]] == ["JOSÉ SOUZA"]
    perfil, _ = _coleta(client, tmp_path, ["MARIA SILVA", "JOSÉ SOUZA"], publicado)
    assert perfil["gabinete_anteriores"] == []  # voltou para a equipe
