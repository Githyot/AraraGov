set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://transparencia.al.ce.gov.br
echo "### API doc"; curl -sSL -A "$ua" --max-time 60 $B/api -o /tmp/a; sed 's/<script.*//' /tmp/a | sed 's/<[^>]*>/\n/g' | tr -s ' \n' | grep -iE "api/|GET|endpoint|/v1|json|parametro|deputad|verba|vota" | head -60 | cut -c1-200
echo "### votacao csv"; curl -sSL -A "$ua" --max-time 120 -D /tmp/h -o /tmp/v "$B/consultas-gerais/votacao-nominal/votacaoNominalcsv"; grep -iE "^(HTTP|content-)" /tmp/h; wc -lc /tmp/v; head -c 1500 /tmp/v | iconv -f latin1 -t utf8 2>/dev/null || head -c 1500 /tmp/v
echo; echo "### votacao form"; curl -sSL -A "$ua" --max-time 60 "$B/consultas-gerais/votacao-nominal" | grep -oE '<(select|input)[^>]*name="[^"]*"[^>]*>|<option[^>]*>[^<]{0,40}' | head -20
echo "### verba"; curl -sSL -A "$ua" --max-time 60 "$B/despesas/verba-desempenho-parlamentar" -o /tmp/vb; grep -oE '(href|action)="[^"#]*"|<(select|input)[^>]*name="[^"]*"' /tmp/vb | grep -iE "csv|xls|json|export|verba|ano|mes|deput|name=" | sort -u | head -25; python3 -c "
import re; h=open('/tmp/vb',encoding='utf-8',errors='replace').read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh])[^>]+>','',h[i:i+2500])))"
