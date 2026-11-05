set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 40 https://www.al.pb.leg.br/transparencia/deputados/viap-v2 -o /tmp/v
echo "### PB scripts"; grep -oE '<script[^>]*src="[^"]*"' /tmp/v | grep -iE "viap|alpb|theme|deput" | head
python3 -c "
import re; h=open('/tmp/v',encoding='utf-8',errors='replace').read()
for s in re.findall(r'<script[^>]*>(.*?)</script>',h,re.S):
  if re.search(r'viap|ajax|fetch|wp-json',s,re.I): print(s[:1500]); print('-----')" | head -80
for js in $(grep -oE 'src="[^"]*(viap|alpb/assets/js)[^"]*"' /tmp/v | cut -d'"' -f2); do echo "### js $js"; curl -sSL -A "$ua" --max-time 40 "$js" | grep -oE "(url|action|fetch|ajax)[^;]{0,160}" | head -15; done
echo "### RR wpdf"; curl -sSL -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/ -o /tmp/r; grep -oE 'wpdf[^"]{0,80}' /tmp/r | sort -u | head -10; grep -oiE 'data-[a-z-]+="[^"]{0,120}"' /tmp/r | grep -iE "wpdf|folder|path|dir|file" | sort -u | head -15
