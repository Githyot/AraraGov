#!/usr/bin/env bash
# Arrecadação e gastos por área (Siconfi).
set -e  # sem pipefail: os diagnósticos dos PRs cortam a saída com head
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov municipios --saida site --sem-eleitos --ufs AC,RR,SP --financas 2023 --limite-siconfi 6
  python -m araragov municipios --saida site --sem-eleitos --ufs AC --mensal 2025 --limite-msc 4 || true
  for f in $(ls site/v1/municipios/*/*/2025-mensal.md | head -1); do echo "== $f"; cat "$f"; done
  for f in $(ls site/v1/municipios/*/*/2023.md | head -2); do
    echo "== $f"; head -30 "$f"; grep -A25 "tabela: areas" "$f" || true; grep -A5 "tabela: sem-dados" "$f" || true
  done
else
  # 2019 até o ano passado. Cada execução busca no máximo 4000 pares município-ano no
  # Siconfi; os outros vêm da publicação anterior e das semanas seguintes.
  python -m araragov municipios --saida site --sem-eleitos --financas 2019-$(( $(date +%Y) - 1 )) --limite-siconfi 4000
  # Mês a mês (MSC) do ano passado e deste ano. Cada execução pede no máximo 6000
  # meses; os fechados vêm da publicação anterior.
  python -m araragov municipios --saida site --sem-eleitos --mensal $(( $(date +%Y) - 1 ))-$(date +%Y) --limite-msc 6000 \
    || echo "MSC mensal incompleta; segue com o que foi publicado"
fi
