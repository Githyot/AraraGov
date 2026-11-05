set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
g() { curl -sSL -A "$ua" --max-time 120 -w "\n== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$@"; }
texto() {
python3 - "$1" "$2" "$3" <<'PY'
import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='replace').read()
txt=re.sub(r'<script.*?</script>|<style.*?</style>|<head.*?</head>','',t,flags=re.S)
txt=html.unescape(re.sub(r'<[^>]+>','\n',txt))
l=[x.strip() for x in txt.splitlines() if x.strip()]
a=int(sys.argv[2]); b=int(sys.argv[3])
print(' | '.join(l[a:b]))
PY
}
echo "### Pagina principal 225-365"
g -o /tmp/dep.html "https://www.camara.leg.br/deputados/204536?ano=2025"; texto /tmp/dep.html 225 365
grep -o 'data-[a-z-]*="[^"]*"' /tmp/dep.html | sort -u | head -30
for sub in verba-gabinete remuneracao pessoal-gabinete; do
  echo "### $sub"
  g -o /tmp/$sub.html "https://www.camara.leg.br/deputados/204536/$sub?ano=2025"
  texto /tmp/$sub.html 0 400 | cut -c1-6000
  grep -oE '<table[^>]*>' /tmp/$sub.html | head -3
done
echo "### outro deputado (com auxilio?) 220593"
g -o /tmp/d2.html "https://www.camara.leg.br/deputados/220593?ano=2025"; texto /tmp/d2.html 330 362
echo "### tabelas de remuneracao"
g -o /tmp/t.html "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/tabelas-de-remuneracao"
grep -oiE 'href="[^"]*"' /tmp/t.html | grep -iE 'pdf|xls|csv|tabela|secret' | sort -u | head -30
g -o /tmp/c.html "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes"
grep -oiE 'href="[^"]*"' /tmp/c.html | grep -iE 'pdf|xls|csv|zip|json|20(25|26)' | sort -u | head -30
echo "### Senado de novo"
g -H "Accept: application/json" -o /tmp/s.json "https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/56/57"; head -c 1500 /tmp/s.json; echo
g -H "Accept: application/json" -o /tmp/v.json "https://legis.senado.leg.br/dadosabertos/votacao?dataInicio=2021-03-01&dataFim=2021-03-31"; head -c 1500 /tmp/v.json; echo
python3 -c "
import json;d=json.load(open('/tmp/v.json'));print(type(d).__name__, len(d))
print([len(x.get('votos') or []) for x in d[:10]] if isinstance(d,list) else '')"
