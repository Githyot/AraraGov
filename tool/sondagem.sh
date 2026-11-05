set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
B=https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar
curl -sSL -A "$ua" --max-time 60 "$B?mes=9&ano=2026" -o /tmp/p
echo "### detalhe"; python3 -c "
import re; h=open('/tmp/p',encoding='utf-8',errors='replace').read(); i=h.find('<tbody'); print(h[i:i+1800])"
echo "### opcoes"; grep -oE '<select name="(ano|mes)"[^>]*>|<option[^>]*value="[^"]*"' /tmp/p | head -30 | tr '\n' ' '
for q in "nome=AGENOR&mes=9&ano=2026" "mes=09&ano=2026" "mes=6&ano=2025&nome=DEP%20AGENOR%20NETO"; do echo; echo "### csv $q"; curl -sSL -A "$ua" --max-time 120 -o /tmp/c "$B/csv?$q"; wc -l /tmp/c; sed -n '2,6p' /tmp/c; done
