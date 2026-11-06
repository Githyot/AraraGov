#!/usr/bin/env bash
# Contratos dos municípios fora de SP (PNCP): junta as partes baixadas em pncp-partes/.
# EVENTO=pull_request junta só a amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov pncp --juntar --partes pncp-partes --saida site --anos 2025 --limite-itens 80
  ls site/v1/municipios/*/*/2025-contratos.md | wc -l
  cat site/v1/municipios/fontes-brutas/pncp-2025.json || true
  f=site/v1/municipios/sc/4208203/2025-contratos.md; [ -f "$f" ] || f=$(ls site/v1/municipios/*/*/2025-contratos.md | head -1)
  head -14 "$f"; grep -A6 "tabela: contratos" "$f" | cut -c1-400
  grep -h "acima da faixa\|Dentro da faixa\|Abaixo da faixa" site/v1/municipios/*/*/2025-contratos.md | head -5 | cut -c1-400
  grep -h "emenda" site/v1/municipios/*/*/2025-contratos.md | grep -v "^| contrato" | head -3 | cut -c1-300 || true
else
  python -m araragov pncp --juntar --partes pncp-partes --saida site
fi
