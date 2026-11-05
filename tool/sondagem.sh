set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
p() { echo "### $1 $2"; curl -sSL -A "$ua" --connect-timeout 20 --max-time 60 -o /tmp/p -w "== %{http_code} %{size_download}B %{url_effective}\n" "$2"; [ -s /tmp/p ] && grep -oiE 'href="[^"#]*"' /tmp/p | sort -u | grep -iE "verba|indeniz|ceap|cota|dados.?abertos|transpar|despesa|gabinete|csv|xls|json|api" | head -12; r=$(echo "$2" | sed -E 's#(https?://[^/]+).*#\1#')/robots.txt; echo "-- robots:"; curl -sSL -A "$ua" --connect-timeout 20 --max-time 30 "$r" | grep -iE "^(user-agent|disallow)" | head -6; }
p AC https://www.al.ac.leg.br/
p AL https://www.al.al.leg.br/
p AM https://www.aleam.gov.br/
p AP https://www.al.ap.gov.br/
p CE https://www.al.ce.gov.br/
p GO https://portal.al.go.leg.br/
p MA https://www.al.ma.leg.br/
p PA https://www.alepa.pa.gov.br/
p PB https://www.al.pb.leg.br/
p PI https://www.alepi.pi.gov.br/
p RN https://www.al.rn.leg.br/
p RO https://www.al.ro.leg.br/
p RR https://www.al.rr.leg.br/
p SE https://www.al.se.leg.br/
p TO https://www.al.to.leg.br/
