set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
ver() { curl -sSL -A "$ua" --max-time 40 -o /tmp/p -w "%{http_code}" "$1" > /tmp/code 2>/dev/null; echo "### $1 -> $(cat /tmp/code) $(wc -c </tmp/p 2>/dev/null)"; grep -oiE '(href|src|action)="[^"#]*"' /tmp/p 2>/dev/null | grep -iE "$2" | sort -u | head -${3:-15}; }
for r in https://www.al.pb.leg.br https://transparencia.al.rr.leg.br https://www.al.ac.leg.br https://www.al.al.leg.br; do echo "### robots $r"; curl -sS -A "$ua" --max-time 20 $r/robots.txt | head -8; done
ver https://www.al.pb.leg.br/transparencia "verba|viap|indeniz|deputad|gabinete|csv|xls|json|remunera|folha|despesa" 30
ver https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/gestao-de-pessoal-intro/ "verba|indeniz|deputad|gabinete|csv|xls|json|remunera|folha|cota" 20
ver https://transparencia.al.rr.leg.br/ "verba|indeniz|deputad|gabinete|cota|parlamentar" 20
ver https://www.al.ac.leg.br/ "transparen|verba|indeniz|gabinete|despesa|cota" 15
ver https://www.al.al.leg.br/ "transparen|verba|indeniz|gabinete|despesa|cota" 15
