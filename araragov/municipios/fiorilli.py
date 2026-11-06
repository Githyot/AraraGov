"""Portais de transparência de prefeituras feitos pela Fiorilli (sistema SCPI).

Muitas prefeituras de estados cujo tribunal de contas não publica dados
abertos (GO, MG, PR, RS, MS, TO...) usam o portal da Fiorilli. Todos têm a
mesma API JSON, em `{site}/Transparencia/VersaoJson/...`, documentada pela
própria Fiorilli ("Dados Abertos Portal Transparência Fiorilli"). A lista de
endpoints e os nomes de campo foram conferidos no projeto Mais Transparência
(github.com/maistransparencia/transparencia, AGPL-3.0).

Não existe uma lista pública dos clientes. `descobrir` testa, para cada
município, os endereços mais comuns do portal e guarda os que respondem em
`araragov/referencia/fiorilli.csv`. Portais atrás de proteção contra robôs
(Cloudflare) ficam de fora: o AraraGov não contorna bloqueios.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import requests

from ..config import USER_AGENT
from .eleitos import municipios_ibge

logger = logging.getLogger(__name__)

CAMINHO = "/Transparencia/VersaoJson/Despesas/"
COLUNAS = ["uf", "ibge", "municipio", "site"]


def _slug(nome: str) -> str:
    from .eleitos import chave_nome

    return chave_nome(nome).lower().replace(" ", "")


def candidatos(uf: str, nome: str) -> List[str]:
    """Endereços em que o portal Fiorilli costuma ficar."""
    s, u = _slug(nome), uf.lower()
    return [
        f"https://transparencia.{s}.{u}.gov.br",
        f"https://{s}.{u}.gov.br",
        f"https://www.{s}.{u}.gov.br",
        f"http://{s}.{u}.gov.br:8079",
        f"http://transparencia.{s}.{u}.gov.br:8079",
    ]


def _parece_fiorilli(texto: str) -> bool:
    """`DefineExercicio` devolve a página de documentação da API ("Dados Abertos Portal
    Transparência Fiorilli"); outras listagens devolvem JSON. O desafio do Cloudflare não passa."""
    t = texto.lstrip()
    if "Portal Transpar" in t[:2000] and "Fiorilli" in t[:2000]:
        return True
    if not t.startswith(("[", "{")):
        return False
    try:
        json.loads(t)
    except ValueError:
        return False
    return True


def responde(sessao, site: str, ano: int, tempo: float = 8) -> bool:
    try:
        r = sessao.get(f"{site}{CAMINHO}", params={"Listagem": "DefineExercicio", "ConectarExercicio": ano},
                       timeout=tempo, allow_redirects=True)
    except requests.RequestException:
        return False
    return r.status_code == 200 and _parece_fiorilli(r.text)


def descobrir(ufs: Optional[Iterable[str]] = None, ano: Optional[int] = None, trabalhadores: int = 48,
              sessao=None) -> List[Dict[str, str]]:
    """Testa os endereços comuns de cada município e devolve os portais Fiorilli que responderam."""
    ano = ano or date.today().year - 1
    filtro = {u.upper() for u in ufs} if ufs else None
    sessao = sessao or requests.Session()
    sessao.headers.setdefault("User-Agent", USER_AGENT)
    municipios = sorted((uf, cod, nome) for (uf, _), (cod, nome) in municipios_ibge().items()
                        if filtro is None or uf in filtro)

    def um(m: Tuple[str, int, str]) -> Optional[Dict[str, str]]:
        uf, cod, nome = m
        for site in candidatos(uf, nome):
            if responde(sessao, site, ano):
                return {"uf": uf, "ibge": str(cod), "municipio": nome, "site": site}
        return None

    with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
        achados = [a for a in ex.map(um, municipios) if a]
    logger.info("Fiorilli: %s portais em %s municípios testados", len(achados), len(municipios))
    return achados


def escrever_lista(achados: List[Dict[str, str]]) -> str:
    saida = io.StringIO()
    saida.write("# Portais Fiorilli encontrados por araragov fiorilli-descobrir\n")
    w = csv.DictWriter(saida, fieldnames=COLUNAS, delimiter=";", lineterminator="\n")
    w.writeheader()
    for a in sorted(achados, key=lambda a: (a["uf"], int(a["ibge"]))):
        w.writerow(a)
    return saida.getvalue()


# --- pagamentos ----------------------------------------------------------------------------

TRIBUNAL = "portal da transparência da prefeitura (Fiorilli)"


def lista() -> List[Dict[str, str]]:
    from importlib import resources

    texto = resources.files("araragov").joinpath("referencia/fiorilli.csv").read_text(encoding="utf-8")
    return list(csv.DictReader((l for l in texto.splitlines() if l.strip() and not l.startswith("#")), delimiter=";"))


def despesas(client, site: str, ano: int) -> List[Dict[str, str]]:
    """Empenhos do ano de todas as entidades do município (prefeitura, câmara, fundos)."""
    dados = client.get_json(f"{site}{CAMINHO}", {
        "Listagem": "DespesasGerais", "ConectarExercicio": ano, "Exercicio": ano, "Ano": ano,
        "DiaInicioPeriodo": "01", "MesInicialPeriodo": "01", "DiaFinalPeriodo": "31", "MesFinalPeriodo": "12",
        "Empresa": 1, "MostraDadosConsolidado": "True", "MostrarFornecedor": "True",
        "MostrarCNPJFornecedor": "True", "UFParaFiltroCOVID": "", "ApenasIDEmpenho": "False"})
    return [{k.upper(): ("" if v is None else str(v)) for k, v in r.items()} for r in (dados or []) if isinstance(r, dict)]


def _valor_br(v: str) -> str:
    """Normaliza para o formato que tcesp.valor lê: '1234.5' (ponto decimal) vira '1234,5'."""
    v = (v or "0").strip()
    if "," not in v and v.count(".") == 1 and len(v.split(".")[1]) <= 2:
        return v.replace(".", ",")
    return v


def traduzir(rs: Iterable[Dict[str, str]], cod: int, nome: str):
    """Empenho da Fiorilli -> linha no formato do TCE-SP (só o valor pago)."""
    from .tcepb import cnpj_valido
    from .tcesp import PAGO, so_digitos

    for r in rs:
        doc = so_digitos(r.get("CPFFORMATADO"))
        pj = cnpj_valido(doc)
        yield {
            "tp_despesa": PAGO,
            "codigo_municipio_ibge": str(cod),
            "ds_municipio": nome,
            "vl_despesa": _valor_br(r.get("PAGO")),
            "ds_elemento": f"{so_digitos(r.get('CATEC'))} - {r.get('NATUREZA') or ''}",
            "tp_identificador_despesa": "CNPJ" if pj else "CPF",
            # Pessoa física (ou CPF mascarado): só um marcador; tcesp guarda só um hash.
            "nr_identificador_despesa": doc if pj else doc[-11:],
            "ds_despesa": r.get("NOMEFOR") or "",
            "ds_funcao_governo": r.get("FUNCAONOME") or "",
            "ds_subfuncao_governo": r.get("SUBFUNCAONOME") or "",
            "ds_orgao": r.get("NOMEEMPRESA") or "",
            "nr_empenho": f"{r.get('EMPRESA') or ''}-{r.get('CODIGO') or r.get('PKEMP') or ''}",
            "ds_acao": r.get("PROJETO_ATIVIDADE_NOME") or "",
            "historico_despesa": r.get("PRODU") or "",
        }


def gerar(client, saida, anos: Iterable[int], limite_municipios: Optional[int] = None,
          hoje: Optional[date] = None, trabalhadores: int = 4) -> int:
    """Gera `{uf}/{ibge}/{ano}-pagamentos.md` das prefeituras com portal Fiorilli conhecido."""
    import os

    from . import publicados, tcesp

    hoje = hoje or date.today()
    portais = lista()[:limite_municipios]

    def um(p: Dict[str, str], ano: int) -> bool:
        uf, cod, nome = p["uf"], int(p["ibge"]), p["municipio"]
        nome_md = f"{ano}-pagamentos.md"
        if (os.environ.get("ARARAGOV_REAPROVEITAR") == "1" and publicados.ano_fechado(ano, hoje)
                and publicados.reaproveitar(client, saida, uf, [cod], nome_md, 1)):
            return True
        try:
            m = tcesp.agregar(traduzir(despesas(client, p["site"], ano), cod, nome)).get(cod)
        except Exception as exc:  # noqa: BLE001 - um portal fora do ar não para os outros
            logger.warning("Fiorilli %s (%s) %s: %s", nome, uf, ano, exc)
            return False
        if not m:
            return False
        m.nome = nome
        caminho = saida / "v1" / "municipios" / uf.lower() / str(cod) / nome_md
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(tcesp.documento(cod, ano, m, hoje, tcesp._governo(saida, cod, ano, uf), uf=uf,
                                           fonte=p["site"] + "/Transparencia/", tribunal=TRIBUNAL), encoding="utf-8")
        return True

    total = 0
    for ano in sorted(anos):
        with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
            feitos = sum(ex.map(lambda p: um(p, ano), portais))
        logger.info("Fiorilli %s: %s de %s prefeituras", ano, feitos, len(portais))
        total += feitos
    return total
