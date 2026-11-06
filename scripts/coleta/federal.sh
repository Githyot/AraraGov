#!/usr/bin/env bash
# Câmara, Senado, assembleias e referências; exporta politicos/ e votacoes/.
# Uma fonte fora do ar (Câmara 504, Senado 503) faz a coleta sair com erro, mas o banco guarda o
# que veio das outras; exporta assim mesmo e devolve o erro no fim.
set -o pipefail
if [ "$EVENTO" = "pull_request" ]; then
  ANO=2025; LIMITE="--limite 30"
else
  # Padrão: a legislatura atual e a anterior (2019 em diante).
  ANO="${ANO_IN:-2019-$(date +%Y)}"; LIMITE="${LIMITE_IN:+--limite $LIMITE_IN}"
fi
python -m araragov coletar tudo --ano "$ANO" $LIMITE
status=$?
python -m araragov exportar --saida site || exit 1
exit $status
