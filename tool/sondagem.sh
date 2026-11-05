set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
for p in gabinetes-parlamentares/csv/2025 despesas/csv/2025; do echo "### $p"; curl -sSL -A "$ua" --max-time 120 -D /tmp/h -o /tmp/c "https://transparencia.alesc.sc.gov.br/$p"; grep -iE "^(HTTP|content-)" /tmp/h; wc -lc /tmp/c; file /tmp/c; head -c 1500 /tmp/c | iconv -f latin1 -t utf8; echo; echo "--- col counts"; awk -F';' '{print NF}' /tmp/c | sort | uniq -c | head; done
echo "### ALEP dados-abertos texto"; curl -sSL -A "$ua" --max-time 60 https://transparencia.assembleia.pr.leg.br/servicos/dados-abertos | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "api|json|csv|deput|verba|ressarc" | head -40 | cut -c1-300
echo "### ALEP robots completo"; curl -sSL -A "$ua" https://transparencia.assembleia.pr.leg.br/robots.txt | tail -n +18
