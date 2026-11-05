set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
g() { curl -sSL -A "$ua" --max-time 120 -w "\n== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$@"; }
echo "### robots"
g "https://www.camara.leg.br/robots.txt" | head -40
echo "### consultar links"
g -o /tmp/p.html "https://www.camara.leg.br/deputados/204536/pessoal-gabinete?ano=2025"
grep -oE '<a[^>]*>[[:space:]]*Consultar' /tmp/p.html | head -3
grep -oE '<tr.{0,1500}?</tr>' <(tr -d '\n' < /tmp/p.html) | sed -n 2p | cut -c1-1500
u=$(grep -oE 'href="[^"]*"[^>]*>[[:space:]]*Consultar' /tmp/p.html | head -1 | sed -E 's/href="([^"]*)".*/\1/' | sed 's/&amp;/\&/g')
echo "URL: $u"
case "$u" in http*) ;; *) u="https://www.camara.leg.br$u";; esac
g -o /tmp/r.html "$u"
python3 - <<'PY'
import re,html
t=open('/tmp/r.html',encoding='utf-8',errors='replace').read()
txt=re.sub(r'<script.*?</script>|<style.*?</style>|<head.*?</head>','',t,flags=re.S)
l=[x.strip() for x in html.unescape(re.sub(r'<[^>]+>','\n',txt)).splitlines() if x.strip()]
i=next((k for k,x in enumerate(l) if 'Kim' in x or 'Remunera' in x),0)
print(' | '.join(l[max(0,i-5):i+150])[:5000])
PY
echo "### auxilio de varios"
for id in 220593 204554 62881 160976 74646 178937 141428 204521; do
  g -s -o /tmp/d.html "https://www.camara.leg.br/deputados/$id?ano=2025" >/dev/null
  python3 - $id <<'PY'
import re,html,sys
t=open('/tmp/d.html',encoding='utf-8',errors='replace').read()
txt=re.sub(r'<script.*?</script>|<style.*?</style>|<head.*?</head>','',t,flags=re.S)
l=[x.strip() for x in html.unescape(re.sub(r'<[^>]+>','\n',txt)).splitlines() if x.strip()]
i=next((k for k,x in enumerate(l) if x=='Pessoal de gabinete'),None)
print(sys.argv[1], ' | '.join(l[i:i+20]) if i else 'sem bloco')
PY
done
echo "### html bruto do bloco de beneficios"
tr -d '\n' < /tmp/d.html | grep -oE 'Imóvel funcional.{0,900}' | head -1
echo "### tabela deputados"
g -o /tmp/t.html "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/tabelas-de-remuneracao/deputadosfederais-1"
grep -oiE 'href="[^"]*"' /tmp/t.html | grep -iE 'pdf|xls|csv|secret|tabela' | sort -u | head -20
