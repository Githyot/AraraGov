set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://www.al.pb.leg.br/transparencia/deputados/viap-v2
curl -sSL -A "$ua" --max-time 40 $B -o /tmp/v
echo "### PB opcoes"; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,30}' /tmp/v | head -30 | tr '\n' ' '; echo; grep -oE '<form[^>]*>' /tmp/v
dep=$(grep -oE '<select name="deputado".*' /tmp/v | head -1)
echo "### PB consulta"; curl -sSL -A "$ua" --max-time 60 "$B?tipo_viap=deputados&ano_viap=2025&mes_viap=9&deputado=" -o /tmp/q; wc -c </tmp/q; python3 -c "
import re; h=open('/tmp/q',encoding='utf-8',errors='replace').read()
print(sorted(set(re.findall(r'href=\"([^\"]*(?:pdf|xls|csv|json|uploads|download)[^\"]*)\"',h,re.I)))[:15])
i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>',' ',h[i:i+2500])) if i>=0 else 'sem tabela')"
echo "### RR set25"; curl -sSL -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/ -o /tmp/r; grep -oiE '(href|src)="[^"#]*"' /tmp/r | grep -iE "pdf|xls|csv|ods|uploads/20|iframe|docs.google|drive" | grep -viE "favicon|\.png|\.jpg" | sort -u | head -20; grep -oE '<iframe[^>]*>' /tmp/r | head
