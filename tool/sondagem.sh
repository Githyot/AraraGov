set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 60 https://www.al.ce.gov.br/deputados -o /tmp/d
echo "### trecho"; python3 -c "
h=open('/tmp/d',encoding='utf-8',errors='replace').read()
i=h.find('deputados/agenor-neto'); print(h[i-900:i+700])
j=h.find('Suplentes em Exerc'); print('---SUP---'); print(h[j-200:j+1500])
import re; print('links', len(set(re.findall(r'al.ce.gov.br/deputados/([a-z0-9-]+)\"',h))))"
echo "### perfil"; curl -sSL -A "$ua" --max-time 60 https://www.al.ce.gov.br/deputados/bruno-pedrosa -o /tmp/p; python3 -c "
import re; h=open('/tmp/p',encoding='utf-8',errors='replace').read()
for k in ['Nome','nome civil','Partido','Nome Civil','Nome completo']:
  i=h.find(k); print(k, re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h[i:i+250])) if i>=0 else None)"
