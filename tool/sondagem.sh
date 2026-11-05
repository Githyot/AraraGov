set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
show() { curl -sSL -A "$ua" --max-time 60 "$1" -o /tmp/p; echo "  bytes: $(wc -c </tmp/p)"; grep -oiE '(href|action|src)="[^"#]*"|<(select|input)[^>]*name="[^"]*"' /tmp/p | grep -viE "fonts|\.css|\.png|\.jpg|\.svg|facebook|instagram|twitter|youtube" | sort -u | head -30; python3 -c "
import re; h=open('/tmp/p',encoding='utf-8',errors='replace').read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>','',h[i:i+1500])) if i>=0 else 'sem tabela')"; }
echo "### robots sigep"; curl -sS -A "$ua" --max-time 30 https://sigep.alepa.pa.gov.br/robots.txt | head -5
for u in https://sigep.alepa.pa.gov.br/transp/frame_verbagabinete.php https://alepa.pa.gov.br/Transparencia/Page/VerbaIndenizatoria https://transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/ https://al.se.leg.br/portal-da-transparencia/despesas/ressarcimento-dos-deputados/ https://www.al.to.leg.br/transparencia/verbaIndenizatoria; do echo "### $u"; show "$u"; done
echo "### PA iframes"; grep -oE '<iframe[^>]*>' /tmp/p | head
curl -sSL -A "$ua" --max-time 60 https://alepa.pa.gov.br/Transparencia/Page/VerbaIndenizatoria | grep -oE '<iframe[^>]*>'
echo "### RN robots api"; curl -sS -A "$ua" --max-time 30 https://api-transparencia.al.rn.leg.br/robots.txt | head -5
echo "### RN js endpoints"; js=$(curl -sSL -A "$ua" --max-time 60 https://transparencia.al.rn.leg.br/ | grep -oE 'main-[A-Z0-9]+\.js' | head -1); curl -sSL -A "$ua" --max-time 60 "https://transparencia.al.rn.leg.br/$js" -o /tmp/js; grep -oE 'apiUrl\+?`?[^`"]{0,10}["`][^"`]{1,80}' /tmp/js | sort -u | head -60; grep -oiE '.{60}verba.{80}' /tmp/js | head -10
