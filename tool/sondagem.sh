set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 60 https://www.al.ce.gov.br/deputados -o /tmp/d
echo "### classes"; grep -oE 'class="deputado_card[^"]*"' /tmp/d | sort | uniq -c
python3 -c "
import re; h=open('/tmp/d',encoding='utf-8',errors='replace').read()
for m in re.finditer(r'class=\"deputado_card([^\"]*)\"(.*?)deputado_card--partido[^>]*>([^<]*)<', h, re.S):
  n=re.search(r'deputados/([a-z0-9-]+)\">\s*([^<]+?)\s*</a>', m.group(2)); print(repr(m.group(1)), n.group(1) if n else None, '|', n.group(2) if n else None, '|', m.group(3).strip(), '| red' if 'red' in m.group(2) else '')" | head -60
