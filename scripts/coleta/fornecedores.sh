#!/usr/bin/env bash
# Fornecedores dos municípios (CEIS/CNEP e campanhas no TSE). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov fornecedores --saida site --ufs SP,SC,CE,PB,PE,RJ,MT --eleicoes 2024
  grep -l "Sanção no\|Fornecedora de campanha" site/v1/municipios/sp/*/fornecedores.md | wc -l
  f=$(grep -l "Fornecedora de campanha" site/v1/municipios/sp/*/fornecedores.md | head -1)
  [ -n "$f" ] && { head -30 "$f"; grep -A6 "tabela: campanha" "$f"; }
  f=$(grep -l "Sanção no" site/v1/municipios/sp/*/fornecedores.md | head -1)
  [ -n "$f" ] && grep -A6 "tabela: sancoes" "$f" || true
else
  # Os pagamentos coletados são do ano passado e do atual, do
  # governo eleito em 2024.
  python -m araragov fornecedores --saida site --ufs todos --eleicoes 2024
fi
