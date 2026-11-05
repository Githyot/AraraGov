set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://www.al.pb.leg.br/transparencia/deputados/viap-v2
curl -sSL -A "$ua" --max-time 40 "$B" -o /tmp/v
echo "### PB selects"; python3 -c "
import re; h=open('/tmp/v',encoding='utf-8',errors='replace').read()
for nome in ['ano_viap','mes_viap','deputado']:
  i=h.find('name=\"'+nome+'\"'); s=h[i:h.find('</select>',i)]; print(nome, re.findall(r'<option[^>]*value=[\"\\']?([^\"\\' >]*)',s)[:8], len(re.findall('<option',s)))
" 
dep=$(python3 -c "
import re; h=open('/tmp/v',encoding='utf-8',errors='replace').read(); i=h.find('name=\"deputado\"'); s=h[i:h.find('</select>',i)]; v=[x for x in re.findall(r'<option[^>]*value=[\"\\']?([^\"\\' >]*)',s) if x not in ('0','')]; print(v[0] if v else '')")
echo "### PB dep=$dep"; curl -sSL -A "$ua" --max-time 60 "$B?tipo_viap=deputados&ano_viap=2025&mes_viap=09&deputado=$dep" -o /tmp/q; python3 -c "
import re; h=open('/tmp/q',encoding='utf-8',errors='replace').read()
print(sorted(set(re.findall(r'href=\"([^\"]*(?:pdf|xls|csv|uploads|download)[^\"]*)\"',h,re.I)))[:10])
i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>',' ',h[i:i+2000])) if i>=0 else 'sem tabela')
j=h.find('Delegado Wallber'); print(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h[j:j+1500])))"
echo "### RR arquivos"; curl -sSL -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/ | grep -oE 'data-(name|path)="[^"]*\.[a-zA-Z]{2,4}"' | head -8
