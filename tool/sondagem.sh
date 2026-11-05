set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
R=https://transparencia.al.ro.leg.br
echo "### RO verba set/2025"; curl -sSL -A "$ua" --max-time 90 "$R/Deputados/VerbaIndenizatoria/?ano=2025&mes=9&categoria=&gabinete=" -o /tmp/r; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,40}' /tmp/r | sed -n '22,40p' | tr '\n' ' '; echo; python3 -c "
import re; h=open('/tmp/r',encoding='utf-8',errors='replace').read()
m=re.search(r'id=\"dados-despesas\"[^>]*>(.*?)</script>',h,re.S); print('json:', m.group(1)[:700] if m else None)
for t in re.findall(r'<table.*?</table>',h,re.S)[:2]: print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b|a\b)[^>]+>',' ',t))[:1500])
print(sorted(set(re.findall(r'href=\"([^\"]*(?:csv|xls|json|pdf|export|download)[^\"]*)\"',h,re.I)))[:15])"
echo "### RO api servidores"; curl -sS -A "$ua" --max-time 90 "$R/api/servidores?cargo=assessor%20parlamentar" -D /tmp/h -o /tmp/a; grep -iE "^(HTTP|content-type)" /tmp/h; head -c 1200 /tmp/a; echo; python3 -c "
import json; d=json.load(open('/tmp/a')); print(type(d).__name__, list(d)[:10] if isinstance(d,dict) else len(d))
x=d if isinstance(d,list) else (d.get('results') or d.get('data') or d.get('servidores') or [])
print(len(x)); import collections; print(collections.Counter(i.get('lotacao') for i in x).most_common(8))"
N=https://api-transparencia.al.rn.leg.br
for p in "verbas/deputados" "verbas/meses/anos" "verbas/despesas/?ano=2025&mes=9" "verbas/despesas/json?ano=2025" "mandato/"; do echo "### RN $p"; curl -sS -A "$ua" --max-time 60 -w "\n%{http_code} %{content_type}\n" "$N/$p" | head -c 900; echo; done
