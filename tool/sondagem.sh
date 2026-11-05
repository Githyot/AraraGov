set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### ALBA lista"; curl -sSL -A "$ua" --max-time 60 https://www.al.ba.gov.br/deputados/legislatura-atual -o /tmp/b; python3 - <<'P'
import re
h=open('/tmp/b',encoding='utf-8',errors='replace').read()
i=h.find('deputado-legislatura-atual/910629'); print(re.sub(r'\s+',' ',h[i-600:i+1800]))
P
echo "### ALBA perfil"; curl -sSL -A "$ua" --max-time 60 https://www.al.ba.gov.br/deputados/deputado-legislatura-atual/910629 | sed 's/<script.*//' | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "partido|nome|exerc|suplent|titular" | head -15 | cut -c1-300
echo "### ALESC deputados sem params"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/deputados | grep -oE 'Mês de referência|fw-semibold">[^<]+|contracheque/[0-9]+\?ano=[0-9]+&amp;mes=[0-9]+' | head -6
echo "### ALESC site deputado"; curl -sSL -A "$ua" --max-time 60 https://www.alesc.sc.gov.br/deputado/paulinha/ | sed 's/<script.*//' | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "partido|nome civil|PODEMOS|PDT|PL |PSD|MDB|PT |exerc" | head -10 | cut -c1-300
curl -sSL -A "$ua" --max-time 60 https://www.alesc.sc.gov.br/robots.txt | head
