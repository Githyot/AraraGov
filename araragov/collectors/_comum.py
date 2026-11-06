"""Rotinas de gravação compartilhadas pelos coletores."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, Iterable, Iterator, List

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ..db import Despesa, Politico, Votacao, Voto

LOTE = 5000


def ler_csv(conteudo: bytes, separador: str = ";") -> Iterator[Dict[str, str]]:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    yield from csv.DictReader(io.StringIO(texto), delimiter=separador)


def gravar_politico(s: Session, dados: Dict[str, Any]) -> Politico:
    """Cria ou atualiza pelo par (casa, codigo)."""
    atual = s.execute(
        select(Politico).where(Politico.casa == dados["casa"], Politico.codigo == dados["codigo"])
    ).scalar_one_or_none()
    if atual is None:
        atual = Politico(**dados)
        s.add(atual)
    else:
        for campo, valor in dados.items():
            if valor is not None or campo == "fonte":
                setattr(atual, campo, valor)
    return atual


def gravar_votacao(s: Session, votacao: Dict[str, Any], votos: List[Dict[str, Any]]) -> None:
    """Grava a votação e substitui todos os votos dela (operação idempotente)."""
    s.merge(Votacao(**votacao))
    s.flush()
    s.execute(delete(Voto).where(Voto.votacao_id == votacao["id"]))
    vistos = set()
    unicos = []
    for v in votos:
        if v["codigo_politico"] in vistos:
            continue
        vistos.add(v["codigo_politico"])
        unicos.append({**v, "votacao_id": votacao["id"]})
    if unicos:
        s.execute(insert(Voto), unicos)


def substituir_despesas(s: Session, casa: str, ano: int, linhas: Iterable[Dict[str, Any]]) -> int:
    """Apaga as despesas do ano e grava as novas. A fonte republica o ano
    inteiro a cada atualização, então substituir é mais seguro que mesclar."""
    s.execute(delete(Despesa).where(Despesa.casa == casa, Despesa.ano == ano))
    total = 0
    lote: List[Dict[str, Any]] = []
    chaves = set()

    def gravar(lote: List[Dict[str, Any]]) -> None:
        # O arquivo de um ano às vezes traz lançamentos datados de outro ano (já gravados
        # pelo arquivo daquele ano); a versão mais recente substitui a anterior.
        s.execute(delete(Despesa).where(Despesa.casa == casa, Despesa.chave_fonte.in_([l["chave_fonte"] for l in lote])))
        s.execute(insert(Despesa), lote)

    for linha in linhas:
        if linha["chave_fonte"] in chaves:
            continue
        chaves.add(linha["chave_fonte"])
        lote.append(linha)
        if len(lote) >= LOTE:
            gravar(lote)
            total += len(lote)
            lote = []
    if lote:
        gravar(lote)
        total += len(lote)
    return total


# --- Nomes -------------------------------------------------------------------

_TITULOS = {"dr", "dra", "doutor", "doutora", "sargento", "sgt", "cabo", "soldado", "coronel", "delegado",
            "delegada", "pastor", "pastora", "padre", "professor", "professora", "prof", "irmao", "irma"}
_LIGACOES = {"da", "de", "do", "das", "dos", "e"}


def _tokens(nome: str) -> List[str]:
    from ..normalizar import _sem_acento

    t = _sem_acento(nome or "").lower().replace(".", " ").replace("-", " ")
    return [p for p in t.split() if p and p not in _LIGACOES and p not in _TITULOS]


def _prefixos_em_ordem(a: List[str], b: List[str]) -> bool:
    j = 0
    for t in a:
        while j < len(b) and not b[j].startswith(t):
            j += 1
        if j == len(b):
            return False
        j += 1
    return True


def _quase_igual(a: str, b: str) -> bool:
    """Igual ou a um erro de digitação de distância (troca, falta, sobra ou
    inversão de uma letra), só para palavras de 4 letras ou mais."""
    if a == b:
        return True
    if min(len(a), len(b)) < 4 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        dif = [i for i in range(len(a)) if a[i] != b[i]]
        return len(dif) == 1 or (len(dif) == 2 and dif[1] == dif[0] + 1 and a[dif[0]] == b[dif[1]] and a[dif[1]] == b[dif[0]])
    curto, longo = sorted((a, b), key=len)
    return any(longo[:i] + longo[i + 1:] == curto for i in range(len(longo)))


def _palavras_em_ordem(a: List[str], b: List[str]) -> bool:
    j = 0
    for t in a:
        while j < len(b) and not _quase_igual(t, b[j]):
            j += 1
        if j == len(b):
            return False
        j += 1
    return True


def casar_nome(nome: str, candidatos: Dict[int, Iterable[str]]) -> Any:
    """Acha o código do político cujo nome (de urna ou civil) corresponde a
    `nome`, como as assembleias escrevem nas planilhas ("Ana Paula da Silva
    (Paulinha)", "Dr Vicente Caropreso"). Só devolve quando há um único
    candidato; na dúvida devolve None, para nunca atribuir gasto à pessoa errada."""
    principal, _, apelido = (nome or "").partition("(")
    variantes = [v for v in (principal, apelido.rstrip(") ")) if v.strip()]
    nomes = {cod: [_tokens(x) for x in lista if x] for cod, lista in candidatos.items()}
    # 1) igual, 2) todas as palavras de um contidas no outro, 3) primeiro e último nome.
    regras = [
        lambda a, b: a == b,
        lambda a, b: len(a) >= 2 and len(b) >= 2 and (set(a) <= set(b) or set(b) <= set(a)),
        lambda a, b: len(a) >= 2 and len(b) >= 2 and a[0] == b[0] and a[-1] == b[-1],
        # "Alex Brasil" x "Alexander Brasil Alves Pereira": cada palavra começa uma palavra do outro, na ordem
        lambda a, b: len(a) >= 2 and _prefixos_em_ordem(a, b),
        # Sobrenome sozinho ("Lunelli"), só se for longo e único
        lambda a, b: len(a) == 1 and len(a[0]) >= 5 and a[0] in b,
        # Erro de digitação da planilha ("Guilherme Samapaio", "Caludio Pinho"): todas as
        # palavras, na ordem, iguais ou a uma letra de distância
        lambda a, b: len(a) >= 2 and _palavras_em_ordem(a, b),
    ]
    for regra in regras:
        achados = {
            cod
            for v in variantes
            for cod, lista in nomes.items()
            for c in lista
            if (t := _tokens(v)) and c and regra(t, c)
        }
        if len(achados) == 1:
            return achados.pop()
        if len(achados) > 1:
            return None
    return None


# --- Planilhas --------------------------------------------------------------

def ler_xlsx(conteudo: bytes) -> List[List[Any]]:
    """Lê a primeira aba de um .xlsx só com a biblioteca padrão.

    Devolve as linhas como listas (células vazias = None). Números saem como
    float; datas do Excel saem como número de dias (ver `data_excel`)."""
    import re
    import zipfile
    import xml.etree.ElementTree as ET

    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = z.namelist()
        compartilhadas: List[str] = []
        if "xl/sharedStrings.xml" in nomes:
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            compartilhadas = ["".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")) for si in raiz.findall("m:si", ns)]
        abas = sorted(n for n in nomes if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        raiz = ET.fromstring(z.read(abas[0]))
    linhas: List[List[Any]] = []
    for row in raiz.iter(f"{{{ns['m']}}}row"):
        linha: List[Any] = []
        for c in row.findall("m:c", ns):
            ref = c.get("r", "")
            letras = "".join(ch for ch in ref if ch.isalpha())
            if letras:
                col = 0
                for ch in letras:
                    col = col * 26 + ord(ch.upper()) - 64
                while len(linha) < col - 1:
                    linha.append(None)
            tipo = c.get("t")
            v = c.find("m:v", ns)
            if tipo == "inlineStr":
                valor: Any = "".join(t.text or "" for t in c.iter(f"{{{ns['m']}}}t"))
            elif v is None or v.text is None:
                valor = None
            elif tipo == "s":
                valor = compartilhadas[int(v.text)]
            elif tipo in ("str", "e"):
                valor = v.text
            elif tipo == "b":
                valor = v.text == "1"
            else:
                valor = float(v.text)
            linha.append(valor)
        linhas.append(linha)
    return linhas


def data_excel(valor: Any):
    """Converte o número de dias do Excel (ou um texto de data) em date."""
    from datetime import date, timedelta

    from ..normalizar import data

    if isinstance(valor, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(valor))
    return data(valor)


# --- Lista oficial de uma assembleia -----------------------------------------

DESLOCAMENTO_SUPLENTE = 1_000_000


def sincronizar_lista_oficial(s: Session, casa: str, uf: str, oficiais: List[Dict[str, Any]]) -> Dict[str, int]:
    """Cruza a lista de deputados em exercício publicada pela assembleia com
    a lista de eleitos do TSE já gravada.

    `oficiais`: dicionários com id (da assembleia), nome e, se houver, nome_civil.
    - Quem está nas duas listas fica em exercício (fonte "tse-assembleia").
    - Quem só está na da assembleia (suplente que assumiu) ganha perfil próprio,
      com código DESLOCAMENTO_SUPLENTE + id e fonte "assembleia".
    - Eleito do TSE que não está na lista oficial fica fora de exercício.
    """
    from .tse import _titulo

    eleitos = {p.codigo: p for p in s.execute(select(Politico).where(Politico.casa == casa)).scalars()}
    candidatos = {cod: [p.nome, p.nome_civil] for cod, p in eleitos.items() if cod < DESLOCAMENTO_SUPLENTE}
    em_exercicio = set()
    novos = 0
    for o in oficiais:
        cod = None
        for nome in (o.get("nome"), o.get("nome_civil")):
            if nome and cod is None:
                cod = casar_nome(nome, candidatos)
        if cod is not None:
            p = eleitos[cod]
            p.em_exercicio = True
            p.fonte = "tse-assembleia"
            if o.get("nome_civil") and not p.nome_civil:
                p.nome_civil = _titulo(o["nome_civil"])
            em_exercicio.add(cod)
            continue
        cod = DESLOCAMENTO_SUPLENTE + int(o["id"])
        nome = o.get("nome") or o.get("nome_civil")
        gravar_politico(s, {
            "casa": casa,
            "cargo": "Deputado estadual",
            "codigo": cod,
            "nome": _titulo(nome) if nome.isupper() else nome,
            "nome_civil": _titulo(o["nome_civil"]) if o.get("nome_civil") else None,
            "partido": o.get("partido"),
            "uf": uf,
            "sexo": None,
            "url_foto": o.get("foto"),
            "email": None,
            "em_exercicio": True,
            "legislatura": 20,
            "fonte": "assembleia",
        })
        em_exercicio.add(cod)
        novos += 1
    fora = 0
    for cod, p in eleitos.items():
        if cod not in em_exercicio:
            p.em_exercicio = False
            fora += 1
    return {"em_exercicio": len(em_exercicio), "suplentes": novos, "fora": fora}
