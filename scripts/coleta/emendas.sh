#!/usr/bin/env bash
# Emendas recebidas pelos municípios (Portal da Transparência). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov emendas-municipios --saida site --ufs AC,SP --anos 2024-2025
  ls site/v1/municipios/*/*/emendas.md | wc -l
  f=site/v1/municipios/sp/3500105/emendas.md; [ -f "$f" ] || f=$(ls site/v1/municipios/ac/*/emendas.md | head -1)
  head -45 "$f"; grep -A12 "tabela: recebido" "$f"
else
  python -m araragov emendas-municipios --saida site
fi
