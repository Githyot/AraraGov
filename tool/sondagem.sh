set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
git fetch -q --depth 1 origin etapa-9-estados && git checkout -q FETCH_HEAD -- araragov pyproject.toml
pip install -q -e . 2>&1 | tail -1
echo "### coleta real"
python -m araragov coletar tse 2>&1 | tail -2
for a in alece-despesas alepa-gabinetes alero-gabinetes; do python -m araragov coletar $a --ano 2026 2>&1 | grep -vE "^\s*$" | tail -4 | cut -c1-900; done
echo "### DF CKAN"
curl -sS -A "$ua" --max-time 60 "https://dados.cl.df.gov.br/api/3/action/package_show?id=tabelas-de-remuneracao" -o /tmp/k; python3 -c "
import json; d=json.load(open('/tmp/k'))['result']
for r in d['resources']: print(r.get('name'),'|',r.get('url'))" | grep -i "subs" | head -30
u=$(python3 -c "
import json; d=json.load(open('/tmp/k'))['result']; rs=[r for r in d['resources'] if 'ubs' in (r.get('name') or '')]; print(rs[-1]['url'] if rs else '')"); echo "ultimo: $u"; curl -sSL -A "$ua" --max-time 60 "$u" | head -20
curl -sS -A "$ua" --max-time 30 https://dados.cl.df.gov.br/robots.txt | head -8
