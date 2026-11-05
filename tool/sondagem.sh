set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 90 https://portalrh.alba.ba.gov.br/transparencia -o /tmp/t
echo "### links/forms"; grep -oiE '(href|action|src|data-url|url)\s*[:=]\s*["'"'"'][^"'"'"']*["'"'"']' /tmp/t | grep -viE "\.css|\.png|\.jpg|fonts|browser-update" | sort -u | head -50
echo "### selects"; grep -oE '<select[^>]*>|<option[^>]*>[^<]{0,60}' /tmp/t | head -40
echo "### texto"; sed 's/<script.*<\/script>//' /tmp/t | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "lota|gabinete|remunera|cargo|export|csv|xls|nome" | head -20 | cut -c1-200
