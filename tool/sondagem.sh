set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 300 -o /tmp/r.csv "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes/2025/dezembro-de-2025-csv"
curl -sSL -A "$ua" --max-time 300 -o /tmp/f.csv "https://dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv"
python3 - <<'PY'
import csv,io,re,collections
pag={}
cargos=collections.Counter()
for r in csv.reader(io.StringIO(open('/tmp/r.csv',encoding='latin-1').read()),delimiter=';'):
    m=re.match(r'(.*?)\s+(\d+)$',r[0])
    if m and r[2]=='Normal':
        pag[m.group(2)]=(m.group(1),r)
        cargos[m.group(1)]+=1
print('pagamento ids',len(pag), cargos.most_common(6))
f=list(csv.DictReader(io.StringIO(open('/tmp/f.csv',encoding='utf-8-sig').read()),delimiter=';'))
print('funcionarios',len(f)); print(f[0])
gab=[x for x in f if 'deputados/' in (x.get('uriLotacao') or '')]
print('em gabinete',len(gab), collections.Counter(x['grupo'] for x in gab).most_common(4))
hit=0; ex=[]
for x in gab:
    n=re.sub(r'\D','',x['ponto'])
    if n in pag:
        hit+=1
        if len(ex)<3: ex.append((x['ponto'],x['cargo'],x['grupo'],pag[n][0],pag[n][1][4:7]))
print('casam pelo ponto',hit,'de',len(gab)); print(ex)
# consistência: grupo/cargo bate?
ok=sum(1 for x in gab if re.sub(r'\D','',x['ponto']) in pag and pag[re.sub(r'\D','',x['ponto'])][0].split()[0].lower() in (x['grupo']+' '+x['cargo']).lower())
print('cargo coerente',ok)
PY
