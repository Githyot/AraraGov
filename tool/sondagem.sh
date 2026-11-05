set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 60 https://www.al.ba.gov.br/transparencia -o /tmp/t; echo "### links RH"; grep -oiE 'href="[^"]*"' /tmp/t | grep -iE "pessoal|servidor|rh|remunera|lotac" | sort -u
for u in https://portalrh.alba.ba.gov.br/transparencia https://portalrh.alba.ba.gov.br/robots.txt; do echo "### $u"; curl -sSL -A "$ua" --max-time 60 "$u" | head -c 1500 | tr -s ' \n'; echo; done
