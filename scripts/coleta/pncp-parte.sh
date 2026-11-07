#!/usr/bin/env bash
# Uma parte das semanas de contratos do PNCP (PARTE=i/n). EVENTO=pull_request baixa só uma amostra.
set -e
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov pncp --parte "$PARTE" --partes pncp-partes --anos 2025 --dias 21
else
  # O job tem 290 min; a parte para de ler aos 250 e grava o que tiver.
  ARARAGOV_PNCP_MINUTOS_PARTE=250 python -m araragov pncp --parte "$PARTE" --partes pncp-partes
fi
ls -la pncp-partes || true
