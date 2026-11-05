set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### ALESP catalogo"; curl -sSL -A "$ua" --max-time 90 https://www.al.sp.gov.br/dados-abertos/catalogo | sed 's/<[^>]*>/\n/g' | tr -s ' \n' | grep -v "^\s*$" | sed -n '1,400p' | grep -iE "vota|xml|deputad|gabinete|servidor|comission|presen" | head -40
curl -sSL -A "$ua" --max-time 90 https://www.al.sp.gov.br/dados-abertos/catalogo | grep -oE 'href="[^"]*(xml|zip|csv|recurso)[^"]*"' | sort -u | head -40
echo "### ALESC servidores"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/servidores -o /tmp/s; grep -oE '(href|hx-get)="[^"]*"' /tmp/s | sort -u | grep -viE "css|font|js" | head -40; python3 -c "
import re; h=open('/tmp/s',encoding='utf-8').read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh])[^>]+>','',h[i:i+2500])))"
