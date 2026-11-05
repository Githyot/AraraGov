"""SINAPI (Caixa/IBGE): custos de referência de obras por estado e mês.

O decreto 7.983/2013 manda usar o SINAPI como referência de preço em obras
com dinheiro federal. A Caixa publica todo mês um pacote em XLSX com os
insumos e as composições (serviços prontos, como "pavimentação com CBUQ")
de todos os estados:

    https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais/SINAPI-AAAA-MM-formato-xlsx.zip

Este módulo baixa o pacote e lê os preços das composições que o AraraGov
usa como referência (referencia/custos_itens.csv).
"""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Any, Dict, Iterator, List

logger = logging.getLogger(__name__)

PACOTE_URL = "https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais/SINAPI-{ano}-{mes:02d}-formato-xlsx.zip"


def baixar(client, ano: int, mes: int) -> bytes:
    return client.get_bytes(PACOTE_URL.format(ano=ano, mes=mes))


def _planilhas(conteudo: bytes) -> Iterator[tuple]:
    """(nome do arquivo, bytes) de cada XLSX do pacote, inclusive zips internos."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in z.namelist():
            dados = z.read(nome)
            if nome.lower().endswith(".zip"):
                for interno in _planilhas(dados):
                    yield (f"{nome}/{interno[0]}", interno[1])
            elif nome.lower().endswith((".xlsx", ".xlsm")):
                yield (nome, dados)


def sondar(conteudo: bytes, linhas: int = 12) -> List[Dict[str, Any]]:
    """Descreve o pacote (arquivos, abas e primeiras linhas), para conferir
    o formato quando a Caixa muda o layout."""
    from openpyxl import load_workbook

    saida = []
    for nome, dados in _planilhas(conteudo):
        wb = load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
        for aba in wb.sheetnames:
            ws = wb[aba]
            amostra = []
            for i, linha in enumerate(ws.iter_rows(values_only=True)):
                if i >= linhas:
                    break
                amostra.append([c for c in linha[:14]])
            saida.append({"arquivo": nome, "aba": aba, "dimensao": ws.max_row, "amostra": amostra})
        wb.close()
    return saida
