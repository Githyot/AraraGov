"""Coleta mensal feita no computador de quem mantém o projeto.

Algumas fontes públicas recusam os servidores do GitHub (a Caixa responde
HTTP 429 e a base de CNPJ da Receita não responde). Estas funções rodam num
computador comum, uma vez por mês, e gravam arquivos pequenos em
`dados/locais/`, que a coleta semanal lê:

- `sinapi/{AAAA-MM}.csv.gz`: custo de cada composição do SINAPI por estado
  (aba CSD, sem desoneração), com código, descrição e unidade.
- `socios.csv.gz`: sócios das empresas que receberam de algum município
  (lista em `cnpjs-fornecedores.txt`), como a Receita publica: nome,
  qualificação, data de entrada e o CPF já mascarado pela própria Receita
  (só 6 dígitos visíveis). Pessoas físicas de fora dessa lista não são
  guardadas.

Uso: `python -m araragov coleta-local --mes 2025-09`.
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
import re
import unicodedata
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

import requests

logger = logging.getLogger(__name__)

SINAPI_URL = "https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais/SINAPI-{ano}-{mes:02d}-formato-xlsx.zip"
RECEITA_RAIZ = "https://arquivos.receitafederal.gov.br/"
RECEITA_DAV = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
CNPJS_URL = "https://githyot.github.io/AraraGov/v1/municipios/cnpjs-fornecedores.txt"
USER_AGENT = "AraraGov/0.1 (dados públicos; github.com/Githyot/AraraGov)"

COLUNAS_SOCIOS = ["cnpj_basico", "tipo", "nome", "cpf_cnpj", "qualificacao", "desde", "faixa_etaria"]
TIPO_SOCIO = {"1": "PJ", "2": "PF", "3": "Estrangeiro"}

_HYPERLINK = re.compile(r",\s*(\d+)\s*\)\s*$")


def _sessao() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    s.max_redirects = 10
    return s


def baixar(sessao: requests.Session, url: str, destino: Path, tentativas: int = 8, espera: float = 30, **kw) -> Path:
    """Download com novas tentativas para 429 e laço de redirecionamento
    (a CDN da Caixa às vezes manda a URL para ela mesma)."""
    for t in range(1, tentativas + 1):
        try:
            with sessao.get(url, stream=True, timeout=(30, 300), **kw) as r:
                if r.status_code == 200:
                    with open(destino, "wb") as f:
                        for parte in r.iter_content(1 << 20):
                            f.write(parte)
                    return destino
                logger.warning("HTTP %s em %s (tentativa %s)", r.status_code, url, t)
                if r.status_code == 404:
                    raise FileNotFoundError(url)
        except requests.TooManyRedirects:
            # A Caixa manda cookies no meio do laço; recomeçar sem eles às vezes resolve.
            sessao.cookies.clear()
            logger.warning("Redirecionamento em laço em %s (tentativa %s de %s)", url, t, tentativas)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            logger.warning("Falha em %s (tentativa %s): %s", url, t, e)
        time.sleep(espera * t)
    raise RuntimeError(f"Não foi possível baixar {url}")


# --- SINAPI ----------------------------------------------------------------------------


def codigo_da_celula(valor) -> Optional[int]:
    """O código da composição vem numa fórmula HYPERLINK(...;104658) sem valor
    calculado; o número é o último argumento."""
    if isinstance(valor, (int, float)) and valor:
        return int(valor)
    if isinstance(valor, str):
        t = valor.strip()
        if t.isdigit():
            return int(t)
        m = _HYPERLINK.search(t)
        if m:
            return int(m.group(1))
    return None


def _sem_acento(texto: str) -> str:
    """Maiúsculas, sem acento e com espaços simples (a planilha da Caixa
    quebra linhas dentro dos cabeçalhos)."""
    t = unicodedata.normalize("NFKD", texto)
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


def composicoes(xlsx: bytes, aba: str = "CSD") -> Iterator[Tuple[int, str, str, str, float]]:
    """(código, descrição, unidade, UF, custo) de cada composição e estado."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx), read_only=True, data_only=False)
    ws = wb[aba]
    ufs: Dict[int, str] = {}
    cabecalho_visto = False
    for linha in ws.iter_rows(values_only=True):
        if not cabecalho_visto:
            # Linha das UFs: siglas de 2 letras nas colunas de custo.
            siglas = {i: str(c).strip() for i, c in enumerate(linha) if isinstance(c, str) and re.fullmatch(r"[A-Z]{2}", c.strip())}
            if len(siglas) >= 20:
                ufs = siglas
            if linha and any(isinstance(c, str) and "CODIGO DA COMPOSICAO" in _sem_acento(c) for c in linha if c):
                cabecalho_visto = True
            continue
        codigo = codigo_da_celula(linha[1] if len(linha) > 1 else None)
        if not codigo:
            continue
        descricao = str(linha[2] or "").strip()
        unidade = str(linha[3] or "").strip()
        for i, uf in ufs.items():
            v = linha[i] if i < len(linha) else None
            if isinstance(v, (int, float)) and v > 0:
                yield codigo, descricao, unidade, uf, float(v)
    wb.close()


def coletar_sinapi(ano: int, mes: int, pasta: Path, sessao: Optional[requests.Session] = None) -> Path:
    sessao = sessao or _sessao()
    tmp = pasta / f"sinapi-{ano}-{mes:02d}.zip"
    pasta.mkdir(parents=True, exist_ok=True)
    # Baixado à mão no navegador (quando a Caixa fica em laço para o script).
    manual = [Path.home() / "Downloads" / f"SINAPI-{ano}-{mes:02d}-formato-xlsx.zip",
              pasta / f"SINAPI-{ano}-{mes:02d}-formato-xlsx.zip"]
    achado = next((m for m in manual if m.exists()), None)
    if achado:
        logger.info("SINAPI: usando o arquivo baixado à mão em %s", achado)
        tmp.write_bytes(achado.read_bytes())
    else:
        baixar(sessao, SINAPI_URL.format(ano=ano, mes=mes), tmp)
    with zipfile.ZipFile(tmp) as z:
        nome = next(n for n in z.namelist() if "Refer" in n and n.lower().endswith(".xlsx"))
        xlsx = z.read(nome)
    tmp.unlink(missing_ok=True)
    destino = pasta / "sinapi" / f"{ano}-{mes:02d}.csv.gz"
    destino.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(destino, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["codigo", "descricao", "unidade", "uf", "custo"])
        for linha in composicoes(xlsx):
            w.writerow([linha[0], linha[1], linha[2], linha[3], f"{linha[4]:.2f}"])
            n += 1
    logger.info("SINAPI %s-%02d: %s preços de composições", ano, mes, n)
    return destino


# --- Receita Federal (sócios) ----------------------------------------------------------


def token_receita(sessao: requests.Session) -> str:
    """A raiz redireciona para o compartilhamento público atual (…/s/TOKEN)."""
    r = sessao.get(RECEITA_RAIZ, timeout=60, allow_redirects=True)
    m = re.search(r"/s/([A-Za-z0-9]+)", r.url) or re.search(r"/s/([A-Za-z0-9]+)", r.text)
    if not m:
        raise RuntimeError("Não achei o compartilhamento público da Receita")
    return m.group(1)


def listar(sessao: requests.Session, token: str, caminho: str = "") -> List[Tuple[str, int]]:
    """(nome, tamanho) dos itens de uma pasta do WebDAV público."""
    r = sessao.request("PROPFIND", RECEITA_DAV + caminho, auth=(token, ""), headers={"Depth": "1"}, timeout=60)
    r.raise_for_status()
    ns = {"d": "DAV:"}
    saida = []
    for resp in ET.fromstring(r.content).findall("d:response", ns):
        href = resp.findtext("d:href", default="", namespaces=ns).rstrip("/").split("/")[-1]
        tamanho = resp.findtext(".//d:getcontentlength", default="0", namespaces=ns)
        saida.append((requests.utils.unquote(href), int(tamanho or 0)))
    return saida[1:]  # o primeiro é a própria pasta


def pasta_cnpj(sessao: requests.Session, token: str) -> str:
    """Caminho da pasta do mês mais recente (ex.: "Dados/Cadastros/CNPJ/2026-10/")."""
    for base in ("", "Dados/Cadastros/CNPJ/"):
        try:
            meses = sorted(n for n, _ in listar(sessao, token, base) if re.fullmatch(r"\d{4}-\d{2}", n))
        except requests.HTTPError:
            continue
        if meses:
            return f"{base}{meses[-1]}/"
    raise RuntimeError("Não achei as pastas mensais do CNPJ")


def linhas_socios(arquivo: Path) -> Iterator[List[str]]:
    with zipfile.ZipFile(arquivo) as z:
        for nome in z.namelist():
            with z.open(nome) as f:
                yield from csv.reader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def filtrar_socios(linhas: Iterable[List[str]], cnpjs: Set[str]) -> Iterator[List[str]]:
    """Só os sócios das empresas da lista (CNPJ básico, 8 dígitos)."""
    for l in linhas:
        if len(l) < 11 or l[0] not in cnpjs:
            continue
        data = l[5]
        desde = f"{data[:4]}-{data[4:6]}-{data[6:8]}" if re.fullmatch(r"\d{8}", data or "") else ""
        yield [l[0], TIPO_SOCIO.get(l[1], l[1]), l[2].strip(), l[3], l[4], desde, l[10]]


def ler_cnpjs(origem: str, sessao: requests.Session) -> Set[str]:
    if origem.startswith("http"):
        texto = sessao.get(origem, timeout=120).text
    else:
        texto = Path(origem).read_text(encoding="utf-8")
    return {re.sub(r"\D", "", l)[:8] for l in texto.splitlines() if re.sub(r"\D", "", l)}


def coletar_socios(pasta: Path, cnpjs: Set[str], cache: Path, sessao: Optional[requests.Session] = None) -> Path:
    sessao = sessao or _sessao()
    token = token_receita(sessao)
    mes = pasta_cnpj(sessao, token)
    cache.mkdir(parents=True, exist_ok=True)
    destino = pasta / "socios.csv.gz"
    pasta.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(destino, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLUNAS_SOCIOS)
        for nome, _ in sorted(listar(sessao, token, mes)):
            if not re.fullmatch(r"Socios\d\.zip", nome):
                continue
            arq = cache / nome
            baixar(sessao, RECEITA_DAV + mes + nome, arq, auth=(token, ""))
            for linha in filtrar_socios(linhas_socios(arq), cnpjs):
                w.writerow(linha)
                n += 1
            arq.unlink(missing_ok=True)
            logger.info("Receita %s%s lido; %s sócios até aqui", mes, nome, n)
    (pasta / "socios-origem.txt").write_text(f"{RECEITA_DAV}{mes} (compartilhamento {token})\n", encoding="utf-8")
    logger.info("Sócios: %s linhas para %s empresas pedidas", n, len(cnpjs))
    return destino


# Palavras para sugerir códigos SINAPI de cada item do catálogo (a escolha
# final é feita à mão em referencia/custos_itens.csv).
PALAVRAS_ITENS = {
    # O SINAPI chama o CBUQ de "concreto asfáltico".
    "pavimentacao-cbuq": ("CONCRETO ASFALTICO",),
    "recape-cbuq": ("FRESAGEM DE PAVIMENTO",),
    "pavimento-intertravado": ("EXECUCAO", "INTERTRAVADO"),
    "paralelepipedo": ("PARALELEP",),
    "drenagem-tubo-600": ("TUBO DE CONCRETO", "AGUAS PLUVIAIS", "DIAMETRO DE 600 MM"),
    "luminaria-led": ("LUMINARIA", "LED", "ILUMINACAO PUBLICA"),
    "poste-concreto": ("ASSENTAMENTO DE POSTE DE CONCRETO",),
}


def candidatos_sinapi(arquivo: Path, destino: Path, uf: str = "SP", por_item: int = 60) -> Path:
    """Lista composições cujas descrições lembram cada item do catálogo."""
    with gzip.open(arquivo, "rt", encoding="utf-8", newline="") as f:
        linhas = [r for r in csv.DictReader(f, delimiter=";") if r["uf"] == uf]
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["item", "codigo", "descricao", "unidade", f"custo_{uf.lower()}"])
        for item, palavras in PALAVRAS_ITENS.items():
            achados = [r for r in linhas if all(p in _sem_acento(r["descricao"]) for p in palavras)]
            for r in achados[:por_item]:
                w.writerow([item, r["codigo"], r["descricao"], r["unidade"], r["custo"]])
    return destino
