set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
g() { curl -sSL -A "$ua" --max-time 180 -w "\n== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$@"; }
echo "### robots www2"; g "https://www2.camara.leg.br/robots.txt" | head -60
echo "### consolidados 2025"
g -o /tmp/c.html "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes/2025"
grep -oiE 'href="[^"]*"' /tmp/c.html | grep -viE 'facebook|twitter|\.css|\.js|portal_|acessibilidade' | sort -u | grep -iE '2025|csv|xls|zip|pdf|json|mes|remun' | head -40
echo "### esclarecimentos"
g -o /tmp/e.html "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes/esclarecimentos-consulta-remuneracao"
python3 -c "
import re,html;t=open('/tmp/e.html',encoding='utf-8',errors='replace').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S);l=[x.strip() for x in html.unescape(re.sub(r'<[^>]+>','\n',t)).splitlines() if x.strip()]
i=next((k for k,x in enumerate(l) if 'sclarec' in x),0);print(' | '.join(l[i:i+60])[:3000])"
echo "### tabela SP"
for u in "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/tabelas-de-remuneracao/tabelafuncaocomissionada" "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/tabelas-de-remuneracao"; do
 g -o /tmp/t.html "$u"; grep -oiE 'href="[^"]*"' /tmp/t.html | grep -iE 'pdf|xls|secret|sp[0-9]|tabela' | sort -u | head -20
 python3 -c "
import re,html;t=open('/tmp/t.html',encoding='utf-8',errors='replace').read()
print([m for m in re.findall(r'(?i)secret[áa]rio parlamentar[^<]{0,200}',t)][:5])"
done
