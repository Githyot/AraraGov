"""Custo de referência em 3 níveis (docs/custo-referencia.md).

Para cada item (ex.: "m² de pavimentação com CBUQ"), estado e ano, calcula
uma **faixa** de quanto aquilo deveria custar:

1. Preço publicado no mesmo estado e ano: tabelas oficiais (SINAPI),
   contratos de outros municípios, artigos e tabelas de empresas.
2. Composição: soma das partes (insumo, frete, mão de obra) com os preços do
   mesmo estado e ano, mais o BDI aceito pelo TCU.
3. Dado esticado: o nível 1 de outro ano (corrigido pelo índice de custo do
   estado, ou pelo IPCA se não houver) ou de um estado vizinho.

O resultado sempre diz o nível e as fontes. Quanto mais esticado o dado,
mais larga a faixa. Em períodos atípicos (pandemia, calamidades) a faixa
também alarga e o app avisa.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources
from statistics import median
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# Estados que fazem fronteira, para o nível 3 (dado de estado vizinho).
VIZINHOS: Dict[str, Tuple[str, ...]] = {
    "AC": ("AM", "RO"), "AL": ("PE", "SE", "BA"), "AP": ("PA",),
    "AM": ("AC", "RO", "MT", "PA", "RR"), "BA": ("SE", "AL", "PE", "PI", "TO", "GO", "MG", "ES"),
    "CE": ("RN", "PB", "PE", "PI"), "DF": ("GO", "MG"), "ES": ("BA", "MG", "RJ"),
    "GO": ("DF", "MG", "BA", "TO", "MT", "MS"), "MA": ("PI", "TO", "PA"),
    "MT": ("RO", "AM", "PA", "TO", "GO", "MS"), "MS": ("MT", "GO", "MG", "SP", "PR"),
    "MG": ("SP", "RJ", "ES", "BA", "GO", "DF", "MS"), "PA": ("AP", "RR", "AM", "MT", "TO", "MA"),
    "PB": ("RN", "CE", "PE"), "PR": ("SP", "MS", "SC"), "PE": ("PB", "CE", "PI", "BA", "AL"),
    "PI": ("MA", "TO", "BA", "PE", "CE"), "RJ": ("ES", "MG", "SP"), "RN": ("CE", "PB"),
    "RS": ("SC",), "RO": ("AC", "AM", "MT"), "RR": ("AM", "PA"), "SC": ("PR", "RS"),
    "SP": ("MG", "RJ", "PR", "MS"), "SE": ("AL", "BA"), "TO": ("MA", "PI", "BA", "GO", "MT", "PA"),
}

ANOS_MAX_ESTICAR = 5
ALARGA_POR_ANO = Decimal("0.05")
ALARGA_VIZINHO = Decimal("0.10")
ALARGA_ATIPICO = Decimal("0.10")
# Faixa mínima em torno de uma única fonte: preço publicado não é exato.
FAIXA_MINIMA = Decimal("0.10")
# BDI de referência para obras (TCU, Acórdão 2.622/2013, 1º e 3º quartis
# para construção de edifícios e obras viárias, arredondados).
BDI = (Decimal("0.20"), Decimal("0.28"))

CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class Item:
    id: str
    descricao: str
    unidade: str
    tipo: str
    sinapi: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Observacao:
    """Um preço publicado (nível 1) para um item, estado e mês."""
    item: str
    uf: str
    competencia: str  # AAAA-MM
    valor: Decimal
    origem: str  # sinapi | contratos | artigo | empresa | tabela-oficial
    fonte: str
    link: str

    @property
    def ano(self) -> int:
        return int(self.competencia[:4])


@dataclass(frozen=True)
class Componente:
    item: str
    componente: str
    quantidade: Decimal


@dataclass(frozen=True)
class PeriodoAtipico:
    inicio: str  # AAAA-MM
    fim: str
    ufs: Tuple[str, ...]  # vazio = Brasil
    tipos: Tuple[str, ...]  # vazio = todos
    descricao: str
    fonte: str

    def afeta(self, uf: str, ano: int, tipo: str) -> bool:
        return (
            int(self.inicio[:4]) <= ano <= int(self.fim[:4])
            and (not self.ufs or uf in self.ufs)
            and (not self.tipos or tipo in self.tipos)
        )


@dataclass
class Referencia:
    item: str
    uf: str
    ano: int
    nivel: int
    minimo: Decimal
    maximo: Decimal
    mediana: Decimal
    metodo: str
    fontes: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    def comparar(self, valor_unitario: Decimal) -> Tuple[str, Optional[Decimal]]:
        """("dentro" | "abaixo" | "acima", % acima do máximo da faixa)."""
        if valor_unitario > self.maximo:
            pct = ((valor_unitario / self.maximo - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
            return "acima", pct
        if valor_unitario < self.minimo:
            return "abaixo", None
        return "dentro", None


# --- leitura das tabelas curadas ---------------------------------------------------


def _csv(nome: str) -> List[Dict[str, str]]:
    texto = resources.files("araragov").joinpath(f"referencia/{nome}").read_text(encoding="utf-8")
    linhas = [l for l in texto.splitlines() if l.strip() and not l.startswith("#")]
    return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(linhas, delimiter=";")]


def carregar_itens() -> Dict[str, Item]:
    return {
        r["id"]: Item(r["id"], r["descricao"], r["unidade"], r["tipo"],
                      tuple(c.strip() for c in r.get("sinapi", "").split(",") if c.strip()))
        for r in _csv("custos_itens.csv")
    }


def carregar_observacoes() -> List[Observacao]:
    """Preços curados à mão. Sem link (http), a linha é ignorada."""
    return [
        Observacao(r["item"], r["uf"].upper(), r["competencia"], Decimal(r["valor"]), r["origem"], r["fonte"], r["link"])
        for r in _csv("custos_observacoes.csv")
        if r.get("link", "").startswith("http") and r.get("valor")
    ]


def carregar_composicoes() -> List[Componente]:
    return [Componente(r["item"], r["componente"], Decimal(r["quantidade"])) for r in _csv("custos_composicoes.csv")]


def carregar_atipicos() -> List[PeriodoAtipico]:
    def lista(t: str) -> Tuple[str, ...]:
        return tuple(x.strip() for x in t.split(",") if x.strip())

    return [
        PeriodoAtipico(r["inicio"], r["fim"], lista(r["ufs"].upper()), lista(r["tipos"]), r["descricao"], r["fonte"])
        for r in _csv("periodos_atipicos.csv")
    ]


# --- cálculo -----------------------------------------------------------------------


def _q(v: Decimal) -> Decimal:
    return v.quantize(CENTAVO, ROUND_HALF_UP)


def _faixa(valores: Sequence[Decimal]) -> Tuple[Decimal, Decimal, Decimal]:
    vs = sorted(valores)
    if len(vs) >= 5:
        vs = vs[1:-1]  # descarta os extremos
    meio = Decimal(median(vs))
    minimo, maximo = vs[0], vs[-1]
    # Uma fonte só (ou fontes muito próximas) não vira preço exato.
    minimo = min(minimo, meio * (1 - FAIXA_MINIMA))
    maximo = max(maximo, meio * (1 + FAIXA_MINIMA))
    return minimo, maximo, meio


def _rotulo(o: Observacao) -> str:
    return f"{o.fonte} ({o.competencia}) {o.link}"


class Calculadora:
    def __init__(
        self,
        itens: Mapping[str, Item],
        observacoes: Iterable[Observacao],
        composicoes: Iterable[Componente] = (),
        atipicos: Iterable[PeriodoAtipico] = (),
        indices: Optional[Mapping[Tuple[str, int], Decimal]] = None,
        ipca_anual: Optional[Mapping[int, Decimal]] = None,
    ):
        self.itens = dict(itens)
        self.obs: Dict[Tuple[str, str, int], List[Observacao]] = {}
        for o in observacoes:
            self.obs.setdefault((o.item, o.uf, o.ano), []).append(o)
        self.comp: Dict[str, List[Componente]] = {}
        for c in composicoes:
            self.comp.setdefault(c.item, []).append(c)
        self.atipicos = list(atipicos)
        self.indices = dict(indices or {})  # (uf, ano) -> índice de custo
        self.ipca = dict(ipca_anual or {})  # ano -> índice acumulado (qualquer base)

    # nível 1
    def _nivel1(self, item: str, uf: str, ano: int) -> Optional[Referencia]:
        obs = self.obs.get((item, uf, ano))
        if not obs:
            return None
        minimo, maximo, meio = _faixa([o.valor for o in obs])
        origens = sorted({o.origem for o in obs})
        return Referencia(item, uf, ano, 1, minimo, maximo, meio,
                          "preço publicado no estado e ano: " + ", ".join(origens),
                          [_rotulo(o) for o in obs])

    # nível 2
    def _nivel2(self, item: str, uf: str, ano: int) -> Optional[Referencia]:
        partes = self.comp.get(item)
        if not partes:
            return None
        minimo = maximo = meio = Decimal(0)
        fontes: List[str] = []
        for p in partes:
            r = self._nivel1(p.componente, uf, ano)
            if r is None:
                return None  # falta o preço de uma parte: não dá para montar
            minimo += p.quantidade * r.minimo
            maximo += p.quantidade * r.maximo
            meio += p.quantidade * r.mediana
            fontes += r.fontes
        bdi_min, bdi_max = BDI
        return Referencia(
            item, uf, ano, 2, minimo * (1 + bdi_min), maximo * (1 + bdi_max),
            meio * (1 + (bdi_min + bdi_max) / 2),
            f"composição ({', '.join(p.componente for p in partes)}) + BDI de {bdi_min:.0%} a {bdi_max:.0%} (TCU, Acórdão 2.622/2013)",
            fontes,
        )

    def _ajuste(self, uf_de: str, ano_de: int, uf_para: str, ano_para: int) -> Tuple[Optional[Decimal], str]:
        de, para = self.indices.get((uf_de, ano_de)), self.indices.get((uf_para, ano_para))
        if de and para:
            return para / de, "índice de custo do estado"
        if uf_de == uf_para and self.ipca.get(ano_de) and self.ipca.get(ano_para):
            return self.ipca[ano_para] / self.ipca[ano_de], "IPCA (sem índice de custo do setor)"
        if uf_de != uf_para and ano_de == ano_para:
            return Decimal(1), "sem ajuste entre estados"
        return None, ""

    # nível 3
    def _nivel3(self, item: str, uf: str, ano: int) -> Optional[Referencia]:
        candidatos: List[Tuple[int, str, int]] = []  # (distância, uf, ano)
        for d in range(1, ANOS_MAX_ESTICAR + 1):
            candidatos += [(d, uf, ano - d), (d, uf, ano + d)]
        candidatos += [(0, v, ano) for v in VIZINHOS.get(uf, ())]
        for d in range(1, ANOS_MAX_ESTICAR + 1):
            candidatos += [(d, v, a) for v in VIZINHOS.get(uf, ()) for a in (ano - d, ano + d)]
        for distancia, uf_de, ano_de in candidatos:
            base = self._nivel1(item, uf_de, ano_de)
            if base is None:
                continue
            fator, como = self._ajuste(uf_de, ano_de, uf, ano)
            if fator is None:
                continue
            alarga = ALARGA_POR_ANO * distancia + (ALARGA_VIZINHO if uf_de != uf else 0)
            de_onde = f"{uf_de} {ano_de}" if uf_de != uf else str(ano_de)
            ref = Referencia(
                item, uf, ano, 3,
                base.minimo * fator * (1 - alarga), base.maximo * fator * (1 + alarga), base.mediana * fator,
                f"dado de {de_onde} levado para {uf} {ano} ({como}); faixa alargada em {alarga:.0%}",
                base.fontes,
            )
            if "IPCA" in como or "sem ajuste" in como:
                ref.avisos.append(f"Ajuste por {como}")
            return ref
        return None

    def referencia(self, item: str, uf: str, ano: int) -> Optional[Referencia]:
        ref = self._nivel1(item, uf, ano) or self._nivel2(item, uf, ano) or self._nivel3(item, uf, ano)
        if ref is None:
            return None
        tipo = self.itens[item].tipo if item in self.itens else ""
        for p in self.atipicos:
            if p.afeta(uf, ano, tipo):
                ref.minimo *= 1 - ALARGA_ATIPICO
                ref.maximo *= 1 + ALARGA_ATIPICO
                ref.avisos.append(f"Período atípico: {p.descricao} ({p.fonte})")
        ref.minimo, ref.maximo, ref.mediana = _q(ref.minimo), _q(ref.maximo), _q(ref.mediana)
        return ref


def calculadora_padrao(
    observacoes_extras: Iterable[Observacao] = (),
    indices: Optional[Mapping[Tuple[str, int], Decimal]] = None,
    ipca_anual: Optional[Mapping[int, Decimal]] = None,
) -> Calculadora:
    return Calculadora(
        carregar_itens(),
        [*carregar_observacoes(), *observacoes_extras],
        carregar_composicoes(),
        carregar_atipicos(),
        indices,
        ipca_anual,
    )


# --- arquivo publicado --------------------------------------------------------------

COLUNAS_REFERENCIAS = ["item", "ano", "nivel", "minimo", "mediana", "maximo", "unidade", "metodo", "fontes", "avisos"]
COLUNAS_ITENS = ["id", "descricao", "unidade", "tipo", "sinapi"]
COLUNAS_ATIPICOS = ["inicio", "fim", "ufs", "tipos", "descricao", "fonte"]


def documento_uf(calc: Calculadora, uf: str, anos: Iterable[int], hoje: Optional[date] = None) -> str:
    from . import md

    hoje = hoje or date.today()
    refs = []
    for item in sorted(calc.itens):
        for ano in sorted(anos):
            r = calc.referencia(item, uf, ano)
            if r:
                refs.append({
                    "item": item, "ano": ano, "nivel": r.nivel, "minimo": r.minimo, "mediana": r.mediana,
                    "maximo": r.maximo, "unidade": calc.itens[item].unidade, "metodo": r.metodo,
                    "fontes": " ; ".join(dict.fromkeys(r.fontes)), "avisos": " ; ".join(r.avisos) or None,
                })
    atip = [p for p in calc.atipicos if not p.ufs or uf in p.ufs]
    return md.escrever(
        {"tipo": "custos-referencia", "uf": uf, "atualizado": hoje, "metodologia": "docs/custo-referencia.md"},
        {
            "referencias": refs,
            "itens": [{"id": i.id, "descricao": i.descricao, "unidade": i.unidade, "tipo": i.tipo,
                       "sinapi": ",".join(i.sinapi) or None} for i in calc.itens.values()],
            "periodos-atipicos": [{"inicio": p.inicio, "fim": p.fim, "ufs": ",".join(p.ufs) or "Brasil",
                                   "tipos": ",".join(p.tipos) or "todos", "descricao": p.descricao,
                                   "fonte": p.fonte} for p in atip],
        },
        colunas={"referencias": COLUNAS_REFERENCIAS, "itens": COLUNAS_ITENS, "periodos-atipicos": COLUNAS_ATIPICOS},
        titulo=f"Custos de referência ({uf})",
        textos={
            "referencias": "## Faixas de referência\n\nNível 1: preço publicado no estado e ano. "
            "Nível 2: composição (insumos, frete, mão de obra e BDI). Nível 3: dado de outro "
            "ano ou de estado vizinho, ajustado. Uma faixa não é preço exato: terreno, "
            "distância e especificação mudam o custo.",
            "itens": "## Itens",
            "periodos-atipicos": "## Períodos atípicos",
        },
    )
