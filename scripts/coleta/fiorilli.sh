#!/usr/bin/env bash
# Pagamentos das prefeituras com portal Fiorilli (lista em araragov/referencia/fiorilli.csv).
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov fiorilli --saida site --anos 2025 --limite-municipios 3
  f=$(ls site/v1/municipios/*/*/2025-pagamentos.md | head -1); head -60 "$f"
else
  python -m araragov fiorilli --saida site --anos 2019-$(date +%Y)
fi
