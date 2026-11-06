import csv
import io
import zipfile

from sqlalchemy import select

from araragov import db
from araragov.collectors import tse

CAMPOS = ["SG_UF", "DS_CARGO", "NR_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO", "NM_SOCIAL_CANDIDATO",
          "NR_CPF_CANDIDATO", "SG_PARTIDO", "DS_GENERO", "NR_TURNO", "DS_SIT_TOT_TURNO"]


def _zip(linhas_por_uf):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("leiame.pdf", b"%PDF")
        for uf, linhas in linhas_por_uf.items():
            s = io.StringIO()
            w = csv.writer(s, delimiter=";", quoting=csv.QUOTE_ALL)
            w.writerow(CAMPOS)
            w.writerows(linhas)
            z.writestr(f"consulta_cand_2022_{uf}.csv", s.getvalue().encode("latin-1"))
    return buf.getvalue()


def test_eleitos_estaduais(client):
    client.bytes(tse.CANDIDATOS_URL.format(ano=2022), _zip({
        "MG": [
            ["MG", "DEPUTADO ESTADUAL", "13123", "MARIA DA SILVA", "MARIA DA SAÚDE", "#NULO", "11111111111", "PT", "FEMININO", "1", "ELEITO POR QP"],
            ["MG", "DEPUTADO ESTADUAL", "22222", "JOSÉ SOUZA", "ZÉ", "#NULO", "2", "PL", "MASCULINO", "1", "SUPLENTE"],
            ["MG", "DEPUTADO FEDERAL", "1313", "OUTRA", "OUTRA", "#NULO", "3", "PT", "FEMININO", "1", "ELEITO"],
            ["MG", "GOVERNADOR", "30", "ROMEU ZEMA NETO", "ROMEU ZEMA", "#NULO", "4", "NOVO", "MASCULINO", "1", "ELEITO"],
            ["MG", "VICE-GOVERNADOR", "30", "MATEUS SIMÕES", "MATEUS SIMÕES", "#NULO", "5", "NOVO", "MASCULINO", "1", "ELEITO"],
        ],
        "SP": [
            ["SP", "GOVERNADOR", "10", "TARCISIO", "TARCÍSIO", "#NULO", "6", "REPUBLICANOS", "MASCULINO", "1", "2º TURNO"],
            ["SP", "GOVERNADOR", "10", "TARCISIO", "TARCÍSIO", "#NULO", "6", "REPUBLICANOS", "MASCULINO", "2", "ELEITO"],
        ],
        "BRASIL": [["MG", "DEPUTADO ESTADUAL", "99999", "DUPLICADO", "DUP", "#NULO", "7", "PT", "FEMININO", "1", "ELEITO"]],
    }))
    assert tse.coletar_eleitos(client) == 4
    with db.sessao() as s:
        ps = {(p.casa, p.codigo): p for p in s.execute(select(db.Politico)).scalars()}
    assert set(ps) == {("al-mg", 13123), ("gov-mg", 300), ("gov-mg", 301), ("gov-sp", 100)}
    maria = ps[("al-mg", 13123)]
    assert (maria.nome, maria.nome_civil, maria.cargo, maria.partido, maria.uf, maria.sexo) == (
        "Maria da Saúde", "Maria da Silva", "Deputado estadual", "PT", "MG", "Feminino")
    assert ps[("gov-mg", 301)].cargo == "Vice-governador"
    # nada de CPF em nenhum campo gravado
    assert all("11111111111" not in str(vars(p)) for p in ps.values())


def test_pula_casas_com_lista_propria(client):
    client.bytes(tse.CANDIDATOS_URL.format(ano=2022), _zip({
        "MG": [["MG", "DEPUTADO ESTADUAL", "13123", "M", "M", "#NULO", "1", "PT", "FEMININO", "1", "ELEITO"]],
    }))
    assert tse.coletar_eleitos(client, pular_casas=("al-mg",)) == 0


def test_url_foto_divulgacand():
    assert tse.url_foto(2024, "160002229427", "77577") == (
        "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2045202024/160002229427/77577")
    assert tse.url_foto(2022, "130001234567", "MG").endswith("/2040602022/130001234567/MG")
    assert tse.url_foto(2022, "#NULO", "MG") is None
    assert tse.url_foto(2010, "1", "MG") is None


def test_eleito_estadual_ganha_foto(client):
    campos = CAMPOS + ["SQ_CANDIDATO"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        s = io.StringIO()
        w = csv.writer(s, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(campos)
        w.writerow(["MG", "DEPUTADO ESTADUAL", "13123", "M", "M", "#NULO", "1", "PT", "FEMININO", "1", "ELEITO",
                    "130001234567"])
        z.writestr("consulta_cand_2022_MG.csv", s.getvalue().encode("latin-1"))
    client.bytes(tse.CANDIDATOS_URL.format(ano=2022), buf.getvalue())
    assert tse.coletar_eleitos(client) == 1
    with db.sessao() as sess:
        p = sess.execute(select(db.Politico)).scalar_one()
    assert p.url_foto == tse.url_foto(2022, "130001234567", "MG")
