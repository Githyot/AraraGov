set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### PB robots *"; curl -sS -A "$ua" --max-time 20 https://www.al.pb.leg.br/robots.txt -o /tmp/r; wc -l /tmp/r; awk '/^User-agent: \*/{f=1} f' /tmp/r | head -20; grep -ciE "^Disallow: /$" /tmp/r; grep -iE "araragov|python|curl" /tmp/r | head
echo "### PB viap"; curl -sSL -A "$ua" --max-time 40 https://www.al.pb.leg.br/transparencia/deputados/viap-v2 -o /tmp/v; wc -c </tmp/v; grep -oiE '(href|src|action|data-url)="[^"#]*"|<(select|input)[^>]*name="[^"]*"' /tmp/v | grep -viE "fonts|\.css|\.png|\.jpg|\.svg|facebook|instagram|twitter|youtube|/transparencia/(?!deputados)" | grep -iE "viap|json|csv|xls|ajax|api|name=|pdf" | sort -u | head -25
echo "### RR verbas"; curl -sSL -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-intro/ -o /tmp/rr; grep -oiE 'href="[^"#]*"' /tmp/rr | grep -iE "verba|indeniz|pdf|xls|csv|ods|uploads" | sort -u | head -25
