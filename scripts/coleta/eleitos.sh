#!/usr/bin/env bash
# Prefeitos, vices e vereadores eleitos (TSE). Os outros passos leem o resumo.md para dizer quem governava.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov municipios --saida site --anos 2024 --ufs AC,RR,SP
  head -40 site/v1/municipios/indice.md
else
  python -m araragov municipios --saida site
fi
