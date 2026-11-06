#!/usr/bin/env bash
# Contratos dos municípios fora de SP (PNCP). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov pncp --saida site --anos 2025 --dias 3 --limite-itens 80
  ls site/v1/municipios/*/*/2025-contratos.md | wc -l
  f=site/v1/municipios/sc/4208203/2025-contratos.md; [ -f "$f" ] || f=$(ls site/v1/municipios/*/*/2025-contratos.md | head -1)
  head -14 "$f"; grep -A6 "tabela: contratos" "$f" | cut -c1-400
  grep -h "acima da faixa\|Dentro da faixa\|Abaixo da faixa" site/v1/municipios/*/*/2025-contratos.md | head -5 | cut -c1-400
  grep -h "emenda" site/v1/municipios/*/*/2025-contratos.md | grep -v "^| contrato" | head -3 | cut -c1-300 || true
else
  python -m araragov pncp --saida site
fi
