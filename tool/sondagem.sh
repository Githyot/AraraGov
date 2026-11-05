set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### ALESC deputados tabela"; curl -sSL -A "$ua" --max-time 60 "https://transparencia.alesc.sc.gov.br/deputados?ano=2025&mes=6" -o /tmp/d; python3 - <<'P'
import re
h=open('/tmp/d',encoding='utf-8',errors='replace').read()
i=h.find('<table'); print(re.sub(r'\s+',' ',h[i:i+5000]))
print('ROWS', h.count('<tr'))
P
echo "### ALEP public API"
for p in "" deputados deputado parlamentares "deputados/legislatura" ressarcimento verbas; do echo "-- /api/public/$p"; curl -sS -A "$ua" --max-time 60 -w "  [HTTP %{http_code} %{content_type}]\n" "http://webservices.assembleia.pr.leg.br/api/public/$p" | head -c 600; echo; done
echo "### ALEP doc paths"; curl -sSL -A "$ua" --max-time 60 https://transparencia.assembleia.pr.leg.br/servicos/dados-abertos | sed 's/<[^>]*>/\n/g' | grep -E "^\s*/[a-z]" | sort -u | head -60
