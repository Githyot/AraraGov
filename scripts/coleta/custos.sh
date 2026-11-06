#!/usr/bin/env bash
# Custos de referência (SIDRA, IPCA e tabelas curadas). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov custos --saida site --ufs PR,SC,SP --anos 2019-2025
  grep -A12 "tabela: referencias" site/v1/referencia/custos/pr.md
else
  python -m araragov custos --saida site
fi
