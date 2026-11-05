set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### PA gabinete form"; curl -sSL -A "$ua" --max-time 60 https://sigep.alepa.pa.gov.br/transp/frame_verbagabinete.php -o /tmp/p; grep -oE '<form[^>]*>|<select[^>]*>|<option[^>]*value="[^"]*"[^>]*>[^<]{0,20}' /tmp/p | head -30
python3 -c "
import re; h=open('/tmp/p',encoding='utf-8',errors='replace').read(); i=h.find('<table'); t=re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>','',h[i:])); print(t[:1200]); print('linhas', t.count('<tr'))"
echo "### PA gabinete set/2025"; curl -sSL -A "$ua" --max-time 60 -d "mes=9&anoref=2025" https://sigep.alepa.pa.gov.br/transp/frame_verbagabinete.php -o /tmp/p2; python3 -c "
import re; h=open('/tmp/p2',encoding='utf-8',errors='replace').read(); i=h.find('<table'); t=re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>','',h[i:])); print(t[:600])"
echo "### PA detalhe"; d=$(grep -oE 'frame_verbadetalhe.php[^"]*' /tmp/p | head -1 | sed 's/&amp;/\&/g'); curl -sSL -A "$ua" --max-time 60 "https://sigep.alepa.pa.gov.br/transp/$d" -o /tmp/d; python3 -c "
import re; h=open('/tmp/d',encoding='utf-8',errors='replace').read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>','',h[i:i+2500])))"
echo "### RO"; curl -sSL -A "$ua" --max-time 60 "https://transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/?ano=2025&mes=9" -o /tmp/r; grep -oE '<select[^>]*>|<option[^>]*value="[^"]*"[^>]*>[^<]{0,30}' /tmp/r | head -40 | tr '\n' ' '; echo; python3 -c "
import re; h=open('/tmp/r',encoding='utf-8',errors='replace').read()
for m in re.finditer(r'<script[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</script>', h, re.S): print(m.group(1), m.group(2)[:800])
i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b)[^>]+>','',h[i:i+1500])))"
echo "### TO"; curl -sSL -A "$ua" --max-time 60 https://www.al.to.leg.br/transparencia/verbaIndenizatoria -o /tmp/t; grep -oE '<option[^>]*value="[^"]*"[^>]*>[^<]{0,30}' /tmp/t | head -12 | tr '\n' ' '; echo; grep -oE '<form[^>]*>' /tmp/t
curl -sSL -A "$ua" --max-time 60 "https://www.al.to.leg.br/transparencia/verbaIndenizatoria?transparencia.ano=2025&transparencia.mes=9&transparencia.parlamentar=&transparencia.tipoTransparencia.codigo=$(grep -oE 'tipoTransparencia.codigo"[^>]*value="[^"]*' /tmp/t | grep -oE '[^"]*$')" -o /tmp/t2; grep -oE 'href="[^"]*(pdf|xls|csv|download|arquivo)[^"]*"' /tmp/t2 | head -10; python3 -c "
import re; h=open('/tmp/t2',encoding='utf-8',errors='replace').read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]\b|a\b)[^>]+>','',h[i:i+1500])) if i>=0 else 'sem tabela')"
echo "### TO robots"; curl -sS -A "$ua" --max-time 30 https://www.al.to.leg.br/robots.txt -o /tmp/tr -w "%{http_code} %{content_type}\n"; grep -i "allow" /tmp/tr | head
