#!/usr/bin/env bash
# Contratos dos municípios do RJ (TCE-RJ). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-rj --saida site --anos 2024 --limite-municipios 5
  f=$(ls site/v1/municipios/rj/*/2024-contratos.md | head -1); head -40 "$f"
else
  python -m araragov tce-rj --saida site --anos $(( $(date +%Y) - 1 ))-$(date +%Y)
fi
