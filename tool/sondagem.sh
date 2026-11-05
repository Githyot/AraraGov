set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
g() { curl -sSL -A "$ua" --max-time 120 -w "\n== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$@"; }
echo "### Pagina do deputado"
g -o /tmp/dep.html "https://www.camara.leg.br/deputados/204536?ano=2025"
python3 - <<'PY'
import re,html
t=open('/tmp/dep.html',encoding='utf-8',errors='replace').read()
txt=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
txt=html.unescape(re.sub(r'<[^>]+>','\n',txt))
linhas=[l.strip() for l in txt.splitlines() if l.strip()]
for i,l in enumerate(linhas):
    if re.search(r'(?i)moradia|im[oó]vel|verba de gabinete|passaporte|miss[aã]o|remunera|sal[aá]rio|cota|pessoal de gabinete|viage',l):
        print(i,' | '.join(linhas[i:i+4])[:300])
for u in sorted(set(re.findall(r'(?:href|src|data-[a-z-]+)="([^"]*(?:verba|gabinete|beneficio|remunera|moradia|viage)[^"]*)"',t,flags=re.I)))[:40]:
    print('URL',u)
PY
echo "### Senado legislatura 56-57"
g -H "Accept: application/json" -o /tmp/s.json "https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/56/57"
python3 -c "
import json;d=json.load(open('/tmp/s.json'));print(list(d)); 
l=d[list(d)[0]]; print(list(l)); ps=l['Parlamentares']['Parlamentar']; print(len(ps)); print(json.dumps(ps[0],ensure_ascii=False)[:1500])"
echo "### Senado votacao sem filtro"
g -H "Accept: application/json" -o /tmp/v.json "https://legis.senado.leg.br/dadosabertos/votacao?dataInicio=2021-03-01&dataFim=2021-03-31&v=1"
python3 -c "
import json;d=json.load(open('/tmp/v.json'));print(type(d).__name__, len(d))
v=d[0] if isinstance(d,list) else d; print(json.dumps(v,ensure_ascii=False)[:800]); print([len(x.get('votos') or []) for x in d[:10]] if isinstance(d,list) else '')"
echo "### Camara remuneracao servidores"
for u in "https://www.camara.leg.br/transparencia/recursos-humanos/remuneracao" "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao" "https://dadosabertos.camara.leg.br/swagger/api.html"; do
  g -o /tmp/r.html "$u"; grep -oiE 'href="[^"]*(csv|xls|zip|json|remunera|folha|funcionario)[^"]*"' /tmp/r.html | sort -u | head -30
done
echo "### Camara dados abertos arquivos (funcionarios)"
for n in funcionarios deputadosOcupacoes deputadosProfissoes; do g -o /tmp/f.csv "https://dadosabertos.camara.leg.br/arquivos/$n/csv/$n.csv"; head -c 600 /tmp/f.csv; echo; done
echo "### Wikidata ideologia (P1142) de partidos e politicos BR"
g -o /tmp/w.json -G "https://query.wikidata.org/sparql" --data-urlencode format=json --data-urlencode 'query=SELECT ?p ?pLabel ?idLabel WHERE { ?p wdt:P1142 ?id; wdt:P27 wd:Q155; wdt:P39 wd:Q18657185 . SERVICE wikibase:label { bd:serviceParam wikibase:language "pt". } } LIMIT 40'
python3 -c "
import json;d=json.load(open('/tmp/w.json'))['results']['bindings'];print(len(d))
[print(x['pLabel']['value'],'|',x['idLabel']['value']) for x in d]"
