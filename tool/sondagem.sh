set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
p() { echo "### $1 $2"; curl -sSL -A "$ua" --connect-timeout 20 --max-time 60 -o /tmp/p -w "== %{http_code} %{size_download}B %{url_effective}\n" "$2"; [ -s /tmp/p ] && grep -oiE '(href|action)="[^"#]*"' /tmp/p | sort -u | grep -iE "${3:-verba|indeniz|ceap|cota|despesa|gabinete|csv|xls|json|api|vota|deputad|parlament}" | head -25; }
p CE https://transparencia.al.ce.gov.br/
curl -sSL -A "$ua" --max-time 30 https://transparencia.al.ce.gov.br/robots.txt | head -5
p CEvot https://transparencia.al.ce.gov.br/consultas-gerais/votacao-nominal
p RN https://transparencia.al.rn.leg.br/transparencia
curl -sSL -A "$ua" --max-time 30 https://transparencia.al.rn.leg.br/robots.txt | head -5
p RO https://transparencia.al.ro.leg.br/
curl -sSL -A "$ua" --max-time 30 https://transparencia.al.ro.leg.br/robots.txt | head -5
p SE https://al.se.leg.br/portal-da-transparencia/
p PB https://www.al.pb.leg.br/transparencia
p PA https://www.alepa.pa.gov.br/Home/Page/PortaldaTransparencia
p AC https://www.al.ac.leg.br/ "transpar|verba|indeniz|cota|despesa|dados"
p AL https://www.al.al.leg.br/ "transpar|verba|indeniz|cota|despesa|dados"
p TO https://www.al.to.leg.br/ "transpar|verba|indeniz|cota|despesa|dados"
p GO https://portal.al.go.leg.br/transparencia "verba|indeniz|cota|despesa|dados|deputad"
