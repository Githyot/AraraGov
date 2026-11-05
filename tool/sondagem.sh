set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/servidores -o /tmp/s
echo "### paginacao/forms"; grep -oE '(href|action|name)="[^"]*(page|pagina|lotacao|vinculo|busca|q=)[^"]*"' /tmp/s | sort -u | head -20; grep -oE '<select[^>]*name="[^"]*"' /tmp/s; grep -oE '<option[^>]*>[^<]*GAB[^<]*' /tmp/s | head -10
python3 - <<'P'
import re,collections
h=open('/tmp/s',encoding='utf-8').read()
rows=re.findall(r'<td class="fw-semibold">([^<]+)</td>\s*<td>([^<]*)</td>\s*<td class="small">([^<]*)</td>',h)
print('ROWS',len(rows)); c=collections.Counter(r[2].strip() for r in rows); print([k for k in c if 'GAB' in k.upper() or 'DEP' in k.upper()][:20]); print(collections.Counter(r[1] for r in rows))
print(re.findall(r'[Pp][aá]gina[^<]{0,60}|de \d+ registros|Total[^<]{0,40}',h)[:5])
P
for q in "?page=2" "?lotacao=GAB" "?vinculo=Comissionado&page=1"; do echo "-- $q"; curl -sSL -A "$ua" --max-time 60 "https://transparencia.alesc.sc.gov.br/servidores$q" | grep -c 'fw-semibold'; done
