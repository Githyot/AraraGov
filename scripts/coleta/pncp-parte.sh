#!/usr/bin/env bash
# Uma parte das semanas de contratos do PNCP (PARTE=i/n). EVENTO=pull_request baixa só uma amostra.
set -e
if [ "$EVENTO" = "pull_request" ]; then
  python -m araragov pncp --parte "$PARTE" --partes pncp-partes --anos 2025 --dias 21
else
  python -m araragov pncp --parte "$PARTE" --partes pncp-partes
fi
ls -la pncp-partes || true
