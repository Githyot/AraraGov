#!/usr/bin/env bash
# Pagamentos dos municípios de SP (TCE-SP). EVENTO=pull_request roda só uma amostra.
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-sp --saida site --anos 2024 --limite-linhas 400000
  f=$(ls site/v1/municipios/sp/*/2024-pagamentos.md | head -1); head -60 "$f"; grep -A8 "tabela: obras" "$f" || true
  echo "== contratos com comparação de custo"
  grep -h -A1 "tabela: obras" site/v1/municipios/sp/*/2024-contratos.md | head -3
  grep -h "acima da faixa\|Dentro da faixa\|Abaixo da faixa" site/v1/municipios/sp/*/2024-contratos.md | head -15
  grep -h -c "Quantidade não informada" site/v1/municipios/sp/*/2024-contratos.md | paste -sd+ | bc
else
  # Ano passado e o atual (o atual ainda muda a cada mês).
  python -m araragov tce-sp --saida site --anos $(( $(date +%Y) - 1 ))-$(date +%Y)
fi
