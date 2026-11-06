#!/usr/bin/env bash
# Pagamentos dos municípios de PE (TCE-PE). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-pe --saida site --anos 2025 --limite-municipios 3
  f=$(ls site/v1/municipios/pe/*/2025-pagamentos.md | head -1); head -60 "$f"
else
  python -m araragov tce-pe --saida site --anos 2019-$(date +%Y)
fi
