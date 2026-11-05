set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 300 -o /tmp/r.csv "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes/2026/setembro-de-2026-csv"
head -c 200 /tmp/r.csv; echo
curl -sSL -A "$ua" --max-time 300 -o /tmp/f.csv "https://dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv"
python3 - <<'PY'
import csv,io,re,collections
vals=collections.Counter()
for r in csv.reader(io.StringIO(open('/tmp/r.csv',encoding='latin-1').read()),delimiter=';'):
    if r and r[0].startswith('Secretário Parlamentar') and len(r)>6 and r[2]=='Normal':
        vals[r[6]]+=1
print('distintos',len(vals))
top=sorted(vals.items(), key=lambda x:-x[1])[:40]
for v,c in sorted(top,key=lambda x: float(x[0].replace('.','').replace(',','.'))): print(v,c)
f=list(csv.DictReader(io.StringIO(open('/tmp/f.csv',encoding='utf-8-sig').read()),delimiter=';'))
niv=collections.Counter(x['cargo'] for x in f if x['grupo']=='Secretário Parlamentar')
print(niv.most_common(40))
PY
