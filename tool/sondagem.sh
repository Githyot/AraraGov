set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
g() { curl -sSL -A "$ua" --max-time 300 -w "\n== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$@"; }
echo "### robots www2 transparencia"; curl -sSL -A "$ua" "https://www2.camara.leg.br/robots.txt" | grep -viE '^Disallow: /[a-z]+$' | head -40
echo "### csv"
g -o /tmp/r.csv "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes/2025/dezembro-de-2025-csv"
file /tmp/r.csv; head -c 300 /tmp/r.csv | xxd | head -5
python3 - <<'PY'
import zipfile,io
b=open('/tmp/r.csv','rb').read()
if b[:2]==b'PK':
    z=zipfile.ZipFile(io.BytesIO(b)); print(z.namelist()); b=z.read(z.namelist()[0])
for enc in ('utf-8-sig','latin-1'):
    try: t=b.decode(enc); break
    except: pass
l=t.splitlines(); print(len(l),'linhas')
for x in l[:4]: print(x[:700])
import collections
sep=';' if l[0].count(';')>l[0].count(',') else ','
cab=[c.strip('"') for c in l[0].split(sep)]; print(cab)
for k,x in enumerate(l[1:]):
    if 'SECRET' in x.upper() and 'PARLAMENTAR' in x.upper():
        print('EX:',x[:700]); break
c=collections.Counter()
for x in l[1:]:
    f=x.split(sep)
    if len(f)>3: c[f[min(3,len(f)-1)][:40]]+=1
print(c.most_common(10))
PY
