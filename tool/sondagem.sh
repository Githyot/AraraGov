set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 120 -o /tmp/c "https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/2025"
curl -sSL -A "$ua" --max-time 120 -o /tmp/c19 "https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/2019"
python3 - <<'P'
import csv,io,collections
for f in ['/tmp/c','/tmp/c19']:
    r=list(csv.DictReader(io.StringIO(open(f,encoding='utf-8-sig').read()),delimiter=';'))
    print('###',f,len(r)); print(r[0].keys())
    for k in ['Verba','Descrição','Conta']:
        c=collections.Counter(x[k] for x in r); print('--',k,len(c)); print(c.most_common(80))
    print('-- amostras com favorecido/trecho', [x for x in r if x['Favorecido'] or x['Trecho']][:5])
P
curl -sSL -A "$ua" --max-time 60 "https://transparencia.alesc.sc.gov.br/deputados?ano=2025&mes=6" | grep -oE 'fw-semibold">[^<]+|contracheque/[0-9]+' | paste - - | head -60
