"""Votações que merecem atenção: temas em que os parlamentares decidem sobre
os próprios benefícios ou recursos.

Não é acusação. O app só destaca que o tema afeta quem está votando, para a
pessoa olhar com calma. As regras são simples e públicas, abaixo.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


def _limpo(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


# (motivo, expressão regular aplicada à ementa + descrição sem acentos)
REGRAS = [
    (
        "Altera salário ou benefícios dos próprios parlamentares",
        r"(subsidio|remuneracao|auxilio[- ]moradia|ajuda de custo|verba de gabinete|cota para o exercicio da atividade parlamentar)"
        r".{0,120}(deputad|senador|membros do congresso|parlamentar)"
        r"|(deputad|senador|membros do congresso|parlamentar).{0,120}(subsidio|remuneracao|auxilio[- ]moradia|ajuda de custo)",
    ),
    ("Trata de fundo eleitoral ou partidário", r"fundo (especial de financiamento de campanha|partidario|eleitoral)"),
    ("Trata de emendas parlamentares ao orçamento", r"emendas? (parlamentar|de relator|individuais|de bancada|pix)"),
    (
        "Trata de anistia ou perdão a partidos ou candidatos",
        r"anistia.{0,80}(partido|candidat|prestacao de contas)|(partido|candidat).{0,80}anistia",
    ),
    ("Trata de imunidade ou foro de parlamentares", r"(imunidade parlamentar|foro (privilegiado|por prerrogativa))"),
]
_COMPILADAS = [(m, re.compile(r)) for m, r in REGRAS]


def motivo_atencao(ementa: Optional[str], descricao: Optional[str] = None) -> Optional[str]:
    texto = _limpo(f"{ementa or ''} {descricao or ''}")
    if not texto:
        return None
    for motivo, regra in _COMPILADAS:
        if regra.search(texto):
            return motivo
    return None
