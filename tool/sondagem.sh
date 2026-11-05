set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### ALESP dados abertos"; curl -sSL -A "$ua" --max-time 90 https://www.al.sp.gov.br/dados-abertos/ | grep -oiE 'href="[^"]*"' | grep -iE "repositorioDados|votac|dados-abertos/" | sort -u | head -60
echo "### ALESP robots"; curl -sSL -A "$ua" --max-time 60 https://www.al.sp.gov.br/robots.txt | head -20
echo "### ALMG ajuda"; curl -sSL -A "$ua" --connect-timeout 30 --max-time 90 https://dadosabertos.almg.gov.br/ws/ajuda/sobre | grep -oiE 'href="[^"]*"' | sort -u | head -60
echo "### ALMG votacoes"; for p in "ws/proposicoes/votacoes" "ws/votacoes" "ws/plenario/votacoes"; do curl -sS -A "$ua" --connect-timeout 30 --max-time 60 -o /tmp/v -w "-- $p %{http_code} %{content_type}\n" "https://dadosabertos.almg.gov.br/$p?formato=json"; head -c 300 /tmp/v; echo; done
echo "### ALESC votacoes"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/sitemap.xml | grep -oE '<loc>[^<]+' | head -40
