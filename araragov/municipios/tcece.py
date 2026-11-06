"""Pagamentos dos municípios do Ceará pelo TCE-CE (SIM, API de dados abertos).

O TCE-CE publica, para cada município, as notas de empenho (com o CNPJ de
quem recebe, a função e o elemento da despesa) e as notas de pagamento (que
apontam para o empenho). Juntamos as duas para ter o valor pago a cada
empresa por área, no mesmo formato `{ano}-pagamentos.md` usado em SP.

Detalhes da API (conferidos no GitHub em 2026-11-05):
- base https://api-dados-abertos.tce.ce.gov.br/sim, respostas em `elements`;
- `exercicio_orcamento` é AAAA00 e `data_referencia_doc` é AAAAMM;
- no máximo 1000 linhas por página (`$count`, `$start_index`);
- o documento de pessoa física já vem cifrado pelo TCE, então nenhum CPF
  chega aqui; pessoas físicas entram só no total.

Os pagamentos contados são os feitos nos meses do próprio exercício do
empenho (restos a pagar pagos no ano seguinte ficam de fora; o texto diz).
"""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

from . import publicados
from . import tcesp
from .tcesp import ELEMENTO_OBRAS, FORA_DO_RANKING, Favorecido, Municipio, _resumir, so_digitos

logger = logging.getLogger(__name__)

BASE = "https://api-dados-abertos.tce.ce.gov.br/sim"
FONTE = "https://api-dados-abertos.tce.ce.gov.br/"
PAGINA = 1000

# Funções de governo (Portaria MOG nº 42/1999), iguais em todo o país.
FUNCOES = {
    "01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "05": "Defesa Nacional", "06": "Segurança Pública", "07": "Relações Exteriores",
    "08": "Assistência Social", "09": "Previdência Social", "10": "Saúde", "11": "Trabalho",
    "12": "Educação", "13": "Cultura", "14": "Direitos da Cidadania", "15": "Urbanismo",
    "16": "Habitação", "17": "Saneamento", "18": "Gestão Ambiental", "19": "Ciência e Tecnologia",
    "20": "Agricultura", "21": "Organização Agrária", "22": "Indústria", "23": "Comércio e Serviços",
    "24": "Comunicações", "25": "Energia", "26": "Transporte", "27": "Desporto e Lazer",
    "28": "Encargos Especiais", "99": "Reserva de Contingência",
}


def paginas(client, recurso: str, params: Dict[str, Any], limite: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    inicio = 0
    while True:
        q = dict(params, **{"$count": PAGINA})
        if inicio:
            q["$start_index"] = inicio
        dados = client.get_json(f"{BASE}/{recurso}", q)
        if isinstance(dados, dict) and dados.get("__errors__"):
            raise RuntimeError(f"TCE-CE recusou {recurso}: {dados['__errors__'][0].get('message', '')[:200]}")
        elementos = (dados or {}).get("elements") or []
        yield from elementos
        inicio += len(elementos)
        if len(elementos) < PAGINA or (limite and inicio >= limite):
            return


def municipios(client) -> List[Tuple[str, int, str]]:
    """(código TCE, IBGE, nome) de cada município."""
    from .eleitos import municipios_ibge

    oficiais = {cod: nome for (uf, _), (cod, nome) in municipios_ibge().items() if uf == "CE"}
    saida = []
    for r in paginas(client, "municipios", {}):
        ibge = r.get("codigo_municipio_ibge")
        if ibge and str(ibge).isdigit():
            ibge = int(ibge)
            saida.append((r["codigo_municipio"], ibge, oficiais.get(ibge) or (r.get("nome_municipio") or "").strip()))
    return saida


def _chave(r: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (str(r.get("codigo_orgao") or "").strip(), str(r.get("codigo_unidade_orcamentaria") or "").strip(),
            str(r.get("data_emissao_empenho") or "")[:10], str(r.get("numero_empenho") or "").strip())


def _valor(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal(0)
    return Decimal(str(v))


def agregar(nome: str, empenhos: Iterable[Dict[str, Any]], pagamentos: Iterable[Dict[str, Any]]) -> Municipio:
    """Junta pagamentos e empenhos no formato do TCE-SP."""
    por_chave = {_chave(e): e for e in empenhos}
    m = Municipio(nome=nome)
    for p in pagamentos:
        if str(p.get("estado_de_estornado") or "0") not in ("0", "False", "false"):
            continue
        e = por_chave.get(_chave(p))
        if e is None:
            continue
        v = _valor(p.get("valor_nota_pagamento"))
        if not v:
            continue
        elemento = so_digitos(e.get("codigo_elemento_despesa"))
        doc = str(e.get("numero_documento_negociante") or "").strip()
        ident = so_digitos(doc) if doc.isdigit() else ""
        if elemento.startswith(FORA_DO_RANKING):
            m.fora_pago += v
            m.fora_pagamentos += 1
            continue
        if len(ident) != 14:
            # Pessoa física (documento cifrado pelo TCE) ou sem documento: só no total.
            m.pf_pago += v
            m.pf_pagamentos += 1
            m.pf_pessoas.add(hashlib.sha1(doc.encode()).hexdigest()[:12])
            continue
        favorecido = _resumir(e.get("nome_negociante"), 120)
        f = m.favorecidos.setdefault(ident, Favorecido(favorecido))
        f.pago += v
        f.pagamentos += 1
        cod = str(e.get("codigo_funcao") or "").strip().zfill(2)
        funcao = FUNCOES.get(cod, f"Função {cod}")
        sub = str(e.get("codigo_subfuncao") or "").strip()
        subfuncao = f"Subfunção {sub}" if sub else ""
        f.areas.add(funcao)
        m.por_area[(funcao, subfuncao)][ident] += v
        m.nomes[ident] = favorecido
        if elemento.startswith(ELEMENTO_OBRAS):
            chave = (str(e.get("codigo_orgao") or "").strip(), str(e.get("numero_empenho") or "").strip())
            o = m.obras.setdefault(chave, {"cnpj": ident, "favorecido": favorecido, "pago": Decimal(0), "acao": None,
                                           "historico": _resumir(e.get("descricao_historico_empenho"))})
            o["pago"] += v
    return m


def coletar(client, codigo: str, ano: int, meses: Iterable[int] = range(1, 13)) -> Tuple[List[Dict], List[Dict]]:
    empenhos: List[Dict] = []
    pagamentos: List[Dict] = []
    for mes in meses:
        q = {"codigo_municipio": codigo, "exercicio_orcamento": ano * 100, "data_referencia_doc": ano * 100 + mes}
        empenhos.extend(paginas(client, "notas_empenhos", q))
        pagamentos.extend(paginas(client, "notas_pagamentos", q))
    return empenhos, pagamentos


def gerar(client, saida: Path, anos: Iterable[int], hoje: Optional[date] = None, limite_municipios: Optional[int] = None,
          trabalhadores: int = 4, meses: Optional[int] = None, novo_client: Optional[Callable[[], Any]] = None) -> int:
    hoje = hoje or date.today()
    lista = municipios(client)
    if limite_municipios:
        lista = lista[:limite_municipios]
    logger.info("TCE-CE: %s municípios", len(lista))
    clientes: Dict[int, Any] = {}
    import threading

    def _client():
        if novo_client is None:
            return client
        t = threading.get_ident()
        if t not in clientes:
            clientes[t] = novo_client()
        return clientes[t]

    def um(tarefa: Tuple[str, int, str, int]) -> int:
        codigo, ibge, nome, ano = tarefa
        ultimo = 12 if ano < hoje.year else hoje.month
        try:
            empenhos, pagamentos = coletar(_client(), codigo, ano, range(1, min(ultimo, meses or 12) + 1))
        except Exception as exc:  # um município fora do ar não derruba os outros
            logger.warning("TCE-CE %s %s: %s", nome, ano, exc)
            return 0
        m = agregar(nome, empenhos, pagamentos)
        if not (m.favorecidos or m.pf_pago or m.fora_pago):
            return 0
        caminho = saida / "v1" / "municipios" / "ce" / str(ibge) / f"{ano}-pagamentos.md"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(tcesp.documento(ibge, ano, m, hoje, tcesp._governo(saida, ibge, ano, "CE"),
                                           uf="CE", fonte=FONTE, tribunal="TCE-CE (SIM)"), encoding="utf-8")
        return 1

    total = 0
    abertos = []
    for a in sorted(anos):
        reaproveitados = publicados.ano_ja_publicado(client, saida, "CE", a, hoje, "{ano}-pagamentos.md")
        total += reaproveitados
        if not reaproveitados:
            abertos.append(a)
    tarefas = [(c, i, n, a) for a in abertos for (c, i, n) in lista]
    with ThreadPoolExecutor(max_workers=max(1, trabalhadores if novo_client else 1)) as ex:
        total += sum(ex.map(um, tarefas))
    logger.info("TCE-CE: %s arquivos de pagamentos", total)
    return total
