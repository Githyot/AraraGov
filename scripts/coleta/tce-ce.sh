#!/usr/bin/env bash
# Pagamentos dos municípios do CE (TCE-CE). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-ce --saida site --anos 2025 --limite-municipios 6 --meses 3
  f=$(ls site/v1/municipios/ce/*/2025-pagamentos.md | head -1); head -50 "$f"; grep -A6 "tabela: obras" "$f" || true
else
  python -m araragov tce-ce --saida site --anos $(( $(date +%Y) - 1 ))-$(date +%Y)
fi
