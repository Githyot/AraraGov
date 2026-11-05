set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
echo "### docigp robots"; curl -sSL -A "$ua" --max-time 60 https://docigp.alerj.rj.gov.br/robots.txt | head -10
echo "### docigp home"; curl -sSL -A "$ua" --max-time 60 -o /tmp/d -w "== %{http_code} %{url_effective}\n" https://docigp.alerj.rj.gov.br/; grep -oiE '(href|src|action)="[^"#]*"' /tmp/d | sort -u | head -40; sed 's/<[^>]*>/ /g' /tmp/d | tr -s ' \n' | head -c 1500; echo
echo "### docigp api"; for p in api api/v1 api/congressmen api/v1/congressmen; do curl -sS -A "$ua" --max-time 30 -o /tmp/a -w "-- /$p %{http_code} %{content_type}\n" "https://docigp.alerj.rj.gov.br/$p"; head -c 300 /tmp/a; echo; done
echo "### titulos relatorios"; for n in 17 33 51 57 58 59 60 61 62 66 72 73 74 75 76 88 103 104 107 108 109 110 111 114 115 117 118 119 120 121 125 129 130 132 134; do t=$(curl -sSL -A "$ua" --max-time 30 "https://transparencia.alerj.rj.gov.br/section/report/$n" | grep -oE '<title>[^<]*|<h[1-3][^>]*>[^<]{3,120}' | sed 's/<[^>]*>//' | tr '\n' '|' | cut -c1-200); echo "$n $t"; done
