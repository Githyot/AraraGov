set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://transparencia.al.ce.gov.br
echo "### robots"; curl -sS -A "$ua" --max-time 30 $B/robots.txt | head
echo "### verba csv"; curl -sSL -A "$ua" --max-time 120 -D /tmp/h -o /tmp/c "$B/despesas/verba-desempenho-parlamentar/csv?mes=9&ano=2026"; grep -iE "^(HTTP|content-)" /tmp/h; wc -lc /tmp/c; head -15 /tmp/c
echo "### verba csv 2025-03"; curl -sSL -A "$ua" --max-time 120 -o /tmp/c2 "$B/despesas/verba-desempenho-parlamentar/csv?mes=3&ano=2025"; wc -l /tmp/c2; head -4 /tmp/c2; cut -d';' -f1 /tmp/c2 | sort | uniq -c | sort -rn | head -5
echo "### api docs"; curl -sSL -A "$ua" --max-time 60 "$B/docs?api-docs.json" -o /tmp/j; python3 -c "
import json; d=json.load(open('/tmp/j'))
for p,v in d.get('paths',{}).items():
  for m,o in v.items(): print(m.upper(),p,'|',(o.get('summary') or '')[:80],'|',[x.get('name') for x in o.get('parameters',[])])"
