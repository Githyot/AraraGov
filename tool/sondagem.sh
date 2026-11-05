set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### robots"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alerj.rj.gov.br/robots.txt | head -20
echo "### home links"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alerj.rj.gov.br/ | grep -oiE '(href|src)="[^"#]*"' | sort -u | head -80
