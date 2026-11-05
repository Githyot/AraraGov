set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
git fetch -q --depth 1 origin etapa-9-estados && git checkout -q FETCH_HEAD -- araragov pyproject.toml
pip install -q -e . 2>&1 | tail -1
echo "### coleta real"
python -m araragov coletar estados-eleitos 2>&1 | grep -iE "erro|error" | tail -3
python -m araragov coletar alece-despesas --ano 2026 2>&1 | grep -iE "ligados" | cut -c1-900
echo "### robots al.ce"; curl -sS -A "$ua" --max-time 30 https://www.al.ce.gov.br/robots.txt | head -15
for u in https://www.al.ce.gov.br/deputados https://www.al.ce.gov.br/paginas/deputados-estaduais; do echo "### $u"; curl -sSL -A "$ua" --max-time 60 -w "%{http_code}\n" "$u" -o /tmp/d; wc -c </tmp/d; grep -oE 'href="[^"]*deputad[^"]*"' /tmp/d | sort -u | head -8; python3 -c "
import re,html; h=open('/tmp/d',encoding='utf-8',errors='replace').read()
for pat in [r'class=\"[^\"]*(?:nome|name|title)[^\"]*\"[^>]*>\s*([^<]{4,60})<', r'<h[2-5][^>]*>\s*([^<]{4,60})</h']:
  xs=re.findall(pat,h); print(len(xs), [html.unescape(x.strip()) for x in xs[:12]])"; done
