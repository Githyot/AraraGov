set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### PERFIL"; curl -sSL -A "$ua" --max-time 60 https://www.al.ba.gov.br/deputados/deputado-legislatura-atual/910629 -o /tmp/p; python3 -c "
h=open('/tmp/p',encoding='utf-8',errors='replace').read()
for k in ['EXERC','Nome:']:
  i=h.find(k); print('--',k,i); print(repr(h[max(0,i-400):i+300]))
"
echo "### NAO EXERCICIO?"; for id in 932169 921283 935220 936939; do curl -sSL -A "$ua" --max-time 60 https://www.al.ba.gov.br/deputados/deputado-legislatura-atual/$id | grep -oE 'EM EXERC[^<]{0,20}|LICENCIAD[^<]{0,30}|AFASTAD[^<]{0,30}|SUPLENTE[^<]{0,30}' | sort | uniq -c | tr '\n' ' '; echo " <- $id"; done
echo "### ALESC ROW"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/deputados -o /tmp/d; python3 -c "
import re
h=open('/tmp/d',encoding='utf-8').read(); i=h.find('<tbody'); print(repr(h[i:i+900])); print('N',len(set(re.findall(r'contracheque/(\d+)',h))))
print(re.findall(r'fw-semibold\">([^<]+)',h))
"
