#!/usr/bin/env bash
# Pagamentos dos municípios da PB (TCE-PB). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov tce-pb --saida site --anos 2025 --limite-linhas 300000
  echo "== valores pagos com vírgula, só com ponto, e exemplos"
  curl -sS -m 300 -A "AraraGov (dados publicos)" https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-2025.zip -o /tmp/pb.zip
  unzip -p /tmp/pb.zip | head -200000 | cut -d';' -f11 | awk '/,/{v++} /^[0-9]+\.[0-9]+$/{p++} END{print "virgula",v,"so_ponto",p}'
  unzip -p /tmp/pb.zip | head -200000 | cut -d';' -f11 | grep ',' | head -5; rm -f /tmp/pb.zip
  f=$(ls site/v1/municipios/pb/*/2025-pagamentos.md | head -1); head -50 "$f"
else
  python -m araragov tce-pb --saida site --anos $(( $(date +%Y) - 1 ))-$(date +%Y)
fi
