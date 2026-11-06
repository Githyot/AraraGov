#!/usr/bin/env bash
# Pagamentos dos municípios da PB (TCE-PB). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-pb --saida site --anos 2025 --limite-linhas 300000
  f=$(ls site/v1/municipios/pb/*/2025-pagamentos.md | head -1); head -50 "$f"
else
  python -m araragov tce-pb --saida site --anos $(( $(date +%Y) - 1 ))-$(date +%Y)
fi
