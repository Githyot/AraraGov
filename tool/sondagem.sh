set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://www.al.pb.leg.br/transparencia/deputados/viap-v2
echo "### PB tipo"; curl -sSL -A "$ua" --max-time 40 "$B?tipo_viap=deputados" -o /tmp/v; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,30}' /tmp/v | head -20 | tr '\n' ' '; echo
echo "### PB ano"; curl -sSL -A "$ua" --max-time 40 "$B?tipo_viap=deputados&ano_viap=2025" -o /tmp/v2; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,30}' /tmp/v2 | head -20 | tr '\n' ' '; echo
echo "### PB mes"; curl -sSL -A "$ua" --max-time 40 "$B?tipo_viap=deputados&ano_viap=2025&mes_viap=9" -o /tmp/v3; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,40}' /tmp/v3 | sed -n '1,12p' | tr '\n' ' '; echo; python3 -c "
import re; h=open('/tmp/v3',encoding='utf-8',errors='replace').read()
print(sorted(set(re.findall(r'href=\"([^\"]*(?:pdf|xls|csv|uploads)[^\"]*)\"',h,re.I)))[:10])
i=h.find('viap-filter-form'); print(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h[i:i+4000]))[:1500])"
echo "### RR wpdf js"; curl -sSL -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/ -o /tmp/r; python3 -c "
import re; h=open('/tmp/r',encoding='utf-8',errors='replace').read()
i=h.find('data-path=\"Ano 2025/\"'); print(re.sub(r'\s+',' ',h[i-600:i+600]))
m=re.search(r'wpdf-custom.js-js-extra\">(.*?)</script>',h,re.S); print(m.group(1)[:600] if m else '')"
