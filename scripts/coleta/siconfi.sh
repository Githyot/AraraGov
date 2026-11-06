#!/usr/bin/env bash
# Arrecadação e gastos por área (Siconfi).
set -eo pipefail
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov municipios --saida site --sem-eleitos --ufs AC,RR,SP --financas 2023 --limite-siconfi 6
  for f in $(ls site/v1/municipios/*/*/2023.md | head -2); do
    echo "== $f"; head -30 "$f"; grep -A25 "tabela: areas" "$f" || true; grep -A5 "tabela: sem-dados" "$f" || true
  done
else
  # 2019 até o ano passado. Cada execução busca no máximo 4000 pares município-ano no
  # Siconfi; os outros vêm da publicação anterior e das semanas seguintes.
  python -m araragov municipios --saida site --sem-eleitos --financas 2019-$(( $(date +%Y) - 1 )) --limite-siconfi 4000
fi
