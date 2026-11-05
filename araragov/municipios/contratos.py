"""Contratos ("ajustes") dos municípios de SP pelo TCE-SP, com a comparação
de custo das obras (fase 4).

Cada contrato de obra é ligado a um item do catálogo de custos
(referencia/custos_itens.csv) pelas palavras do objeto. Quando o contrato
traz a quantidade numa unidade que bate com a do item (m², m, unidade), o
valor unitário é comparado com a faixa de referência do estado e do ano
(v1/referencia/custos/sp.md). Sem quantidade, o contrato aparece sem
comparação, com o motivo.

Também aponta, sem acusar, a mesma empresa com várias contratações diretas
(dispensa ou inexigibilidade) no mesmo ano.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import md
from .tcesp import BASE, FONTE, _resumir, baixar, formatar_cnpj, so_digitos, valor

logger = logging.getLogger(__name__)

PAGINA = "https://transparencia.tce.sp.gov.br/conjunto-de-dados"
TOP_CONTRATOS = 60
MIN_DIRETAS = 3  # contratações diretas da mesma empresa no ano para aparecer

# (item do catálogo, palavras que precisam aparecer, palavras que excluem)
REGRAS: List[Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = [
    ("recape-cbuq", ("recape",), ()),
    ("recape-cbuq", ("fresagem",), ()),
    ("pavimento-intertravado", ("intertravad",), ()),
    ("pavimento-intertravado", ("bloquete",), ()),
    ("paralelepipedo", ("paralelep",), ()),
    ("pavimentacao-cbuq", ("paviment", "asfalt"), (" tapa ", "manutenc")),
    ("pavimentacao-cbuq", ("cbuq",), (" tapa ",)),
    ("drenagem-tubo-600", ("drenagem",), ()),
    ("luminaria-led", ("lumin", " led "), ()),
    ("poste-concreto", (" poste",), ("sinaliza",)),
]

# Prédios: só obra nova ou ampliação. Reforma, pintura, piso, vidro e
# manutenção não se comparam com o custo do m² de um prédio inteiro.
PREDIOS = (("creche", (" creche",)), ("ubs", (" unidade basica de saude", " ubs ")),
           ("hospital", (" hospital",)), ("escola", (" escola", " unidade escolar", " predio escolar")))
OBRA_NOVA = ("construc", "constru ", "ampliac", "edificac")
NAO_PREDIO = ("reforma", "pintura", "piso", "vidro", "manutenc", "aquisic", "fornecimento", "locac", "limpeza",
              "aliment", "material", "uniforme", "transporte", "telhado", "cobertura", "reparo", "adequac")

# Nomes que o TCE-SP grafa diferente do IBGE.
NOMES_TCESP = {"FLORINEA": 3516101}

# Fora desta proporção da faixa, o mais provável é quantidade ou unidade
# cadastrada errado (ex.: obra inteira lançada como "1 m²"); não se compara.
LIMITE_COERENCIA = Decimal(10)

SEM_FAIXA = "Sem faixa de referência para este item e ano"
MIN_CONTRATOS_FAIXA = 10  # contratos no estado e ano para formar a faixa

UNIDADES = {
    "m²": ("M2", "M²", "METRO QUADRADO", "METROS QUADRADOS", "MT2"),
    "m": ("M", "ML", "METRO", "METROS", "METRO LINEAR", "MT"),
    "un": ("UN", "UND", "UNID", "UNIDADE", "UNIDADES", "PC", "PECA"),
}

COLUNAS_OBRAS = ["contrato", "cnpj", "empresa", "orgao", "modalidade", "objeto", "valor", "quantidade", "unidade",
                 "item", "valor_unitario", "ref_minimo", "ref_maximo", "nivel", "comparacao", "aviso"]
COLUNAS_CONTRATOS = ["contrato", "cnpj", "empresa", "orgao", "modalidade", "objeto", "valor", "assinatura"]
COLUNAS_DIRETAS = ["cnpj", "empresa", "contratacoes", "valor", "fundamentos"]


def _norm(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def classificar(objeto: str) -> Optional[str]:
    # Espaços nas pontas e pontuação trocada por espaço, para casar palavras
    # inteiras: " poste" casa "postes" mas não "posterior".
    t = " " + re.sub(r"[^a-z0-9 ]", " ", _norm(objeto)) + " "
    if re.search(r" posterior", t):
        t = t.replace(" posterior", " ")
    for item, precisa, exclui in REGRAS:
        if all(p in t for p in precisa) and not any(e in t for e in exclui):
            return item
    if any(o in t + " " for o in OBRA_NOVA) and not any(e in t for e in NAO_PREDIO):
        for item, nomes in PREDIOS:
            if any(n in t for n in nomes):
                return item
    return None


def unidade(texto: str) -> Optional[str]:
    t = _norm(texto).upper().replace(".", "").strip()
    for u, nomes in UNIDADES.items():
        if t in nomes:
            return u
    return None


def _quantidade(texto: str) -> Decimal:
    return valor(texto)


def referencias_sp(saida: Path) -> Dict[Tuple[str, int], Dict[str, str]]:
    caminho = saida / "v1" / "referencia" / "custos" / "sp.md"
    if not caminho.exists():
        return {}
    doc = md.ler(caminho.read_text(encoding="utf-8"))
    return {(r["item"], int(r["ano"])): r for r in doc.tabelas.get("referencias", [])}


def links_ajustes(client, ano: int) -> List[str]:
    html = client.get_bytes(PAGINA).decode("utf-8", "replace")
    achados = re.findall(r'href="([^"]*licitacoes-contratos/ajustes-%d[^"]*\.zip)"' % ano, html)
    return sorted({("https://transparencia.tce.sp.gov.br" + h) if h.startswith("/") else h for h in achados})


def linhas_ajustes(arquivo: Path) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(arquivo) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".csv"):
                with z.open(nome) as f:
                    yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""), delimiter=";")


def _campo(l: Dict[str, str], *inicios: str) -> str:
    for chave, v in l.items():
        if chave and any(_norm(chave).startswith(_norm(i)) for i in inicios):
            return (v or "").strip()
    return ""


def comparar(item: Optional[str], unid: Optional[str], qtd: Decimal, total: Decimal,
             refs: Dict[Tuple[str, int], Dict[str, str]], ano: int, unidades_itens: Dict[str, str]) -> Dict[str, Any]:
    vazio = {"valor_unitario": None, "ref_minimo": None, "ref_maximo": None, "nivel": None}
    if not item:
        return {**vazio, "comparacao": "Tipo de obra não identificado no objeto", "aviso": None}
    if not unid or qtd <= 0:
        return {**vazio, "comparacao": "Quantidade não informada no contrato", "aviso": None}
    if qtd <= 1:
        return {**vazio, "comparacao": "Contrato por preço global (quantidade 1); comparação não feita", "aviso": None}
    ref = refs.get((item, ano))
    aviso = None
    if ref is None and unidades_itens.get(item) == "m²" and item in ("creche", "escola", "ubs", "hospital"):
        ref = refs.get(("edificacao-media", ano))
        aviso = "Referência genérica: custo médio do m² do SINAPI (prédios residenciais padrão)"
    if unidades_itens.get(item) != unid:
        return {**vazio, "comparacao": f"Unidade do contrato ({unid}) diferente da referência ({unidades_itens.get(item)})", "aviso": None}
    unitario = (total / qtd).quantize(Decimal("0.01"))
    if ref is None:
        return {**vazio, "valor_unitario": unitario, "comparacao": SEM_FAIXA, "aviso": None}
    minimo, maximo = Decimal(ref["minimo"]), Decimal(ref["maximo"])
    if unitario > maximo * LIMITE_COERENCIA or unitario * LIMITE_COERENCIA < minimo:
        return {**vazio, "valor_unitario": unitario,
                "comparacao": "Quantidade ou unidade incoerente com o valor (provável erro de cadastro); comparação não feita",
                "aviso": None}
    if unitario > maximo:
        texto = f"{((unitario / maximo - 1) * 100).quantize(Decimal('0.1'))}% acima da faixa de referência"
    elif unitario < minimo:
        texto = "Abaixo da faixa de referência"
    else:
        texto = "Dentro da faixa de referência"
    avisos = "; ".join(a for a in (aviso, ref.get("avisos")) if a) or None
    return {"valor_unitario": unitario, "ref_minimo": minimo, "ref_maximo": maximo, "nivel": ref.get("nivel"),
            "comparacao": texto, "aviso": avisos}


def agregar(linhas: Iterable[Dict[str, str]], ano: int, refs, unidades_itens) -> Dict[str, Dict[str, Any]]:
    """Por município (nome, como no arquivo): obras, maiores contratos e contratações diretas."""
    por_mun: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"obras": [], "contratos": [], "diretas": defaultdict(lambda: {"n": 0, "valor": Decimal(0), "fund": set(), "empresa": ""})})
    vistos = set()
    for l in linhas:
        mun = _campo(l, "Município", "Municipio")
        cnpj = so_digitos(_campo(l, "CNPJ da empresa"))
        cod = _campo(l, "Código do Ajuste", "Codigo do Ajuste")
        if not mun or (mun, cod) in vistos:
            continue
        vistos.add((mun, cod))
        total = valor(_campo(l, "Valor total do contrato")) or valor(_campo(l, "Valor da Nota de Empenho"))
        objeto = _campo(l, "Descrição do objeto contratado") or _campo(l, "Descrição do objeto da licitação")
        modalidade = _campo(l, "Modalidade")
        empresa = _resumir(_campo(l, "Nome da empresa"), 120)
        base = {
            "contrato": _campo(l, "Nº do contrato", "N do contrato") or cod,
            "cnpj": formatar_cnpj(cnpj) if len(cnpj) == 14 else None,
            "empresa": empresa if len(cnpj) == 14 else "Pessoa física (sem nome)",
            "orgao": _resumir(_campo(l, "Entidade"), 80),
            "modalidade": modalidade,
            "objeto": _resumir(objeto),
            "valor": total,
        }
        m = por_mun[mun]
        m["contratos"].append({**base, "assinatura": _campo(l, "Vigência do contrato - Data Assinatura", "Vigencia do contrato - Data Assinatura") or None})
        item = classificar(objeto)
        if item:
            unid = unidade(_campo(l, "Unidade do objeto"))
            qtd = _quantidade(_campo(l, "Quantidade do objeto"))
            m["obras"].append({**base, "quantidade": qtd if unid else None, "unidade": unid, "item": item,
                               **comparar(item, unid, qtd, total, refs, ano, unidades_itens)})
        if "contratacao direta" in _norm(modalidade) and len(cnpj) == 14:
            d = m["diretas"][cnpj]
            d["n"] += 1
            d["valor"] += total
            d["empresa"] = empresa
            fund = _campo(l, "Fundamento Legal")
            if fund:
                d["fund"].add(_resumir(fund, 60))
    return por_mun


def _quartil(valores: List[Decimal], q: float) -> Decimal:
    v = sorted(valores)
    pos = (len(v) - 1) * q
    i = int(pos)
    j = min(i + 1, len(v) - 1)
    return (v[i] + (v[j] - v[i]) * Decimal(str(pos - i))).quantize(Decimal("0.01"))


def faixas_dos_contratos(por_mun: Dict[str, Dict[str, Any]], ano: int) -> Dict[Tuple[str, int], Dict[str, str]]:
    """Nível 1 pelos preços contratados no estado: para cada item sem faixa
    publicada, a faixa vai do 1º ao 3º quartil do valor por unidade dos
    contratos de SP no ano (pelo menos 10 contratos)."""
    precos: Dict[str, List[Decimal]] = defaultdict(list)
    for m in por_mun.values():
        for o in m["obras"]:
            if o.get("comparacao") == SEM_FAIXA and o.get("valor_unitario"):
                precos[o["item"]].append(o["valor_unitario"])
    faixas = {}
    for item, v in precos.items():
        if len(v) < MIN_CONTRATOS_FAIXA:
            continue
        faixas[(item, ano)] = {
            "minimo": str(_quartil(v, 0.25)), "maximo": str(_quartil(v, 0.75)), "nivel": "1",
            "avisos": f"Faixa dos preços contratados por municípios de SP no ano (1º ao 3º quartil de {len(v)} contratos, TCE-SP)",
        }
    return faixas


def comparar_com_contratos(por_mun: Dict[str, Dict[str, Any]], ano: int, unidades_itens: Dict[str, str]) -> int:
    faixas = faixas_dos_contratos(por_mun, ano)
    n = 0
    for m in por_mun.values():
        for o in m["obras"]:
            if o.get("comparacao") == SEM_FAIXA and (o["item"], ano) in faixas:
                o.update(comparar(o["item"], o["unidade"], o["quantidade"], o["valor"], faixas, ano, unidades_itens))
                n += 1
    return n


def documento(ibge: int, mun: str, ano: int, dados: Dict[str, Any], hoje: date) -> str:
    obras = sorted(dados["obras"], key=lambda r: r["valor"], reverse=True)
    contratos = sorted(dados["contratos"], key=lambda r: r["valor"], reverse=True)[:TOP_CONTRATOS]
    diretas = sorted(
        ({"cnpj": formatar_cnpj(c), "empresa": d["empresa"], "contratacoes": d["n"], "valor": d["valor"],
          "fundamentos": " | ".join(sorted(d["fund"])) or None}
         for c, d in dados["diretas"].items() if d["n"] >= MIN_DIRETAS),
        key=lambda r: r["valor"], reverse=True,
    )
    return md.escrever(
        {"tipo": "municipio-contratos", "ibge": ibge, "municipio": mun, "uf": "SP", "ano": ano,
         "atualizado": hoje, "fonte": FONTE, "metodologia": "docs/custo-referencia.md"},
        {"obras": obras, "contratos": contratos, "contratacoes-diretas": diretas},
        colunas={"obras": COLUNAS_OBRAS, "contratos": COLUNAS_CONTRATOS, "contratacoes-diretas": COLUNAS_DIRETAS},
        titulo=f"{mun} (SP), contratos de {ano}",
        textos={
            "obras": "## Obras e o custo de referência\n\nValor unitário do contrato comparado com a faixa "
            "de referência do estado e do ano. Acima da faixa não quer dizer irregular: terreno, "
            "distância e especificação mudam o preço. É um ponto para perguntar.",
            "contratos": "## Maiores contratos do ano",
            "contratacoes-diretas": "## Mesma empresa com várias contratações diretas\n\n"
            f"Empresas com {MIN_DIRETAS} ou mais contratações sem licitação (dispensa ou inexigibilidade) "
            "no ano. A lei permite; a soma serve para conferir se compras parecidas foram divididas.",
        },
    )


def gerar(client, saida: Path, anos: Iterable[int], hoje: Optional[date] = None, pasta_tmp: Optional[Path] = None) -> int:
    from .custos import carregar_itens
    from .eleitos import chave_nome, municipios_ibge

    hoje = hoje or date.today()
    pasta_tmp = pasta_tmp or saida.parent / "tmp"
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    refs = referencias_sp(saida)
    unidades_itens = {i.id: i.unidade for i in carregar_itens().values()}
    ibge = {nome: cod for (uf, nome), (cod, _) in municipios_ibge().items() if uf == "SP"}
    total = 0
    for ano in sorted(anos):
        arquivos = []
        for i, url in enumerate(links_ajustes(client, ano)):
            arq = pasta_tmp / f"ajustes-{ano}-{i}.zip"
            baixar(client, url, arq)
            arquivos.append(arq)
        if not arquivos:
            logger.warning("TCE-SP: nenhum arquivo de contratos de %s na página", ano)
            continue
        por_mun = agregar((l for a in arquivos for l in linhas_ajustes(a)), ano, refs, unidades_itens)
        logger.info("TCE-SP contratos %s: %s obras comparadas com a faixa dos contratos do estado",
                    ano, comparar_com_contratos(por_mun, ano, unidades_itens))
        for mun, dados in por_mun.items():
            cod = ibge.get(chave_nome(mun)) or NOMES_TCESP.get(chave_nome(mun))
            if not cod:
                logger.warning("TCE-SP: município sem código IBGE: %s", mun)
                continue
            caminho = saida / "v1" / "municipios" / "sp" / str(cod) / f"{ano}-contratos.md"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(documento(cod, mun, ano, dados, hoje), encoding="utf-8")
            total += 1
        for a in arquivos:
            a.unlink(missing_ok=True)
        logger.info("TCE-SP contratos %s: %s municípios", ano, len(por_mun))
    return total
