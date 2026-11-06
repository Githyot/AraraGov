#!/usr/bin/env bash
# Sondar fontes municipais (alcance a partir do GitHub). EVENTO=pull_request roda só uma amostra.
set -eo pipefail
for u in \
  "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20250101&dataFinal=20250102&codigoModalidadeContratacao=6&uf=AC&pagina=1" \
  "https://apisidra.ibge.gov.br/values/t/2296/n3/41/v/48/p/202501" \
  "https://dadosabertos.tce.pr.gov.br/" \
  "https://transparencia.tce.sp.gov.br/" \
  "https://dados.tce.rs.gov.br/" \
  "https://api.obrasgov.gestao.gov.br/obrasgov/api/projeto-investimento?pagina=1&tamanhoDaPagina=1" \
  "https://arquivos.receitafederal.gov.br/" \
  "https://portaldatransparencia.gov.br/download-de-dados/ceis" ; do
  code=$(curl -s -o /tmp/r -w '%{http_code} %{size_download}B %{time_total}s' -m 40 -A "AraraGov (dados publicos; github.com/Githyot/AraraGov)" "$u" || echo "falhou")
  echo "$code  $u"; head -c 300 /tmp/r 2>/dev/null; echo
done
