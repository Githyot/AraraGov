import csv
import io
import zipfile
from datetime import date

from araragov.collectors.tse import CANDIDATOS_URL
from araragov.municipios import eleitos, md

CAMPOS = ["SG_UF", "SG_UE", "NM_UE", "NM_TIPO_ELEICAO", "CD_ELEICAO", "DS_CARGO", "NR_CANDIDATO", "SQ_CANDIDATO",
          "NM_CANDIDATO", "NM_URNA_CANDIDATO", "NM_SOCIAL_CANDIDATO", "NR_CPF_CANDIDATO", "DT_NASCIMENTO",
          "SG_PARTIDO", "DS_GENERO", "NR_TURNO", "DS_SIT_TOT_TURNO"]
ORD = "ELEIÇÃO ORDINÁRIA"


def _zip(ano, linhas_por_uf):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("leiame.pdf", b"%PDF")
        for uf, linhas in linhas_por_uf.items():
            s = io.StringIO()
            w = csv.writer(s, delimiter=";", quoting=csv.QUOTE_ALL)
            w.writerow(CAMPOS)
            w.writerows(linhas)
            z.writestr(f"consulta_cand_{ano}_{uf}.csv", s.getvalue().encode("latin-1"))
    return buf.getvalue()


def _l(uf, ue, nome_ue, cargo, num, nome, partido, turno, sit, tipo=ORD, cpf="12345678901"):
    return [uf, ue, nome_ue, tipo, "619", cargo, num, f"1{num}", nome, nome.split()[0], "#NULO", cpf,
            "01/01/1970", partido, "FEMININO", turno, sit]


def test_eleitos_e_arquivos(client, tmp_path):
    client.bytes(CANDIDATOS_URL.format(ano=2024), _zip(2024, {
        "PR": [
            _l("PR", "75310", "CAMPO MOURÃO", "PREFEITO", "45", "ANA DA SILVA", "PSDB", "1", "2º TURNO"),
            _l("PR", "75310", "CAMPO MOURÃO", "PREFEITO", "45", "ANA DA SILVA", "PSDB", "2", "ELEITO"),
            _l("PR", "75310", "CAMPO MOURÃO", "PREFEITO", "13", "BRUNO SOUZA", "PT", "2", "NÃO ELEITO"),
            _l("PR", "75310", "CAMPO MOURÃO", "VICE-PREFEITO", "45", "CARLA LIMA", "PSD", "2", "#NULO"),
            _l("PR", "75310", "CAMPO MOURÃO", "VICE-PREFEITO", "13", "DANI REIS", "PT", "2", "#NULO"),
            _l("PR", "75310", "CAMPO MOURÃO", "VEREADOR", "45123", "EDU COSTA", "PSDB", "1", "ELEITO POR QP"),
            _l("PR", "75310", "CAMPO MOURÃO", "VEREADOR", "13999", "FABI NUNES", "PT", "1", "SUPLENTE"),
            _l("PR", "74004", "ABATIÁ", "PREFEITO", "22", "GIL MOTA", "PL", "1", "ELEITO", tipo="ELEIÇÃO SUPLEMENTAR"),
        ],
        "MG": [_l("MG", "43010", "OLHOS-D'ÁGUA", "PREFEITO", "10", "HELO PIRES", "REPUBLICANOS", "1", "ELEITO")],
        "SP": [_l("SP", "71072", "SÃO PAULO", "PREFEITO", "15", "IVO ALVES", "MDB", "1", "ELEITO")],
    }))
    total = eleitos.gerar(client, tmp_path, anos=[2024], ufs=["PR", "MG"], hoje=date(2026, 11, 5))
    assert total == 2  # Abatiá só tem eleição suplementar; SP ficou fora do filtro

    base = tmp_path / "v1" / "municipios"
    doc = md.ler((base / "pr" / "4104303" / "resumo.md").read_text(encoding="utf-8"))
    assert doc.meta["municipio"] == "Campo Mourão" and doc.meta["tse"] == "75310"
    mandatos = doc.tabelas["mandatos"]
    assert [(r["cargo"], r["nome"], r["partido"]) for r in mandatos] == [
        ("Prefeito", "Ana", "PSDB"), ("Vice-prefeito", "Carla", "PSD"), ("Vereador", "Edu", "PSDB")]
    assert mandatos[0]["inicio"] == "2025" and mandatos[0]["fim"] == "2028"
    assert mandatos[1]["situacao"] == "Eleito"
    texto = (base / "pr" / "4104303" / "resumo.md").read_text(encoding="utf-8")
    assert "12345678901" not in texto and "1970" not in texto

    # nome com apóstrofo: TSE "OLHOS D'ÁGUA", IBGE "Olhos d'Água"
    assert (base / "mg" / "3145455" / "resumo.md").exists()

    indice = md.ler((base / "indice.md").read_text(encoding="utf-8")).tabelas["municipios"]
    assert [(r["uf"], r["municipio"], r["prefeito"], r["vereadores"]) for r in indice] == [
        ("MG", "Olhos d'Água", "Helo", "0"), ("PR", "Campo Mourão", "Ana", "1")]


def test_eleicao_sem_dados_vira_aviso_com_responsavel(client, tmp_path):
    client.bytes(CANDIDATOS_URL.format(ano=2020), _zip(2020, {"PR": []}))
    client.bytes(CANDIDATOS_URL.format(ano=2024), _zip(2024, {
        "PR": [_l("PR", "75310", "CAMPO MOURÃO", "PREFEITO", "45", "ANA DA SILVA", "PSDB", "1", "ELEITO")],
    }))
    eleitos.gerar(client, tmp_path, anos=[2020, 2024], ufs=["PR"], hoje=date(2026, 11, 5))
    doc = md.ler((tmp_path / "v1/municipios/pr/4104303/resumo.md").read_text(encoding="utf-8"))
    falta = doc.tabelas["sem-dados"]
    assert len(falta) == 1 and falta[0]["esfera"] == "federal" and "2020" in falta[0]["motivo"]
    assert falta[0]["responsavel"] == "Tribunal Superior Eleitoral (TSE)"


def test_chave_nome():
    assert eleitos.chave_nome("Olhos-d'Água") == eleitos.chave_nome("OLHOS D'AGUA") == "OLHOS D AGUA"


def test_lista_do_ibge_e_correcoes():
    ibge = eleitos.municipios_ibge()
    assert len(ibge) >= 5570
    assert ibge[("PR", eleitos.chave_nome("CAMPO MOURÃO"))][0] == 4104303
    correcoes = eleitos.correcoes_tse_ibge()
    codigos = {c for c, _ in ibge.values()}
    assert correcoes and set(correcoes.values()) <= codigos
