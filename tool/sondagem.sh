set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 90 https://portalrh.alba.ba.gov.br/transparencia | grep -oE 'href="https://portalrh.alba.ba.gov.br/transparencia/[0-9]+"[^>]*>[^<]*' | sort -u
for t in 0 1 2 3; do echo "### tab $t"; curl -sSL -A "$ua" --max-time 120 -o /tmp/j$t "https://portalrh.alba.ba.gov.br/transparencia/$t"; python3 - $t <<'P'
import json,sys,collections
t=sys.argv[1]
try:
  d=json.load(open(f'/tmp/j{t}'))
except Exception as e:
  print('ERR',e,open(f'/tmp/j{t}','rb').read(200)); sys.exit()
rows=d.get('data',d) if isinstance(d,dict) else d
print('N',len(rows)); print(rows[:2])
lot=collections.Counter(r.get('lotacao') for r in rows)
print('GAB', [ (k,v) for k,v in lot.items() if k and ('GAB' in k.upper() or 'DEP' in k.upper())][:15])
print('SIMB', collections.Counter(r.get('simbolo') for r in rows).most_common(10))
print('CARGO', collections.Counter(r.get('cargoFuncao') for r in rows).most_common(8))
P
done
