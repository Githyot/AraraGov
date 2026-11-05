set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### ALESC deputados"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/deputados -o /tmp/d; grep -oE '<(tr|td|a|div|span|img)[^>]*>[^<]{0,80}' /tmp/d | grep -viE "menu|nav|footer" | sed -n '120,260p' | cut -c1-250
echo "### ALESC certidao"; curl -sSL -A "$ua" --max-time 60 https://transparencia.alesc.sc.gov.br/deputados/certidao-subsidio | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "subs|R\\$|lei|resolu" | head -20 | cut -c1-300
echo "### ALEP API robots"; curl -sSL -A "$ua" --max-time 60 http://webservices.assembleia.pr.leg.br/robots.txt | head -20
echo "### ALEP endpoints"; curl -sSL -A "$ua" --max-time 60 https://transparencia.assembleia.pr.leg.br/servicos/dados-abertos | grep -oE '(/api/public[^"<& ]*|GET[^<]{0,120}|POST[^<]{0,120})' | sort -u | head -60
