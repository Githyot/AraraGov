#!/usr/bin/env bash
# Pagamentos das prefeituras com portal Agili/IPM (quase todas do MT). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov agili --saida site --anos 2025 --limite-municipios 3
  ls site/v1/municipios/*/*/2025-pagamentos.md | wc -l
  f=$(ls site/v1/municipios/*/*/2025-pagamentos.md | head -1); head -60 "$f"
else
  python -m araragov agili --saida site --anos 2019-$(date +%Y)
fi
