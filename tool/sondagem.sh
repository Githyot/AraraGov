set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
links() { echo "### $1"; curl -sSL -A "$ua" --max-time 60 -o /tmp/x -w "== HTTP %{http_code} %{content_type} %{size_download}B\n" "$1"; grep -oiE 'href="[^"#]*"' /tmp/x | sed 's/href=//' | sort -u | grep -iE "${2:-deput|verba|despes|ressarc|indeniz|api|json|csv|dados|gabinete|diaria|cota|parlament|remunera}" | head -45; }
links "https://transparencia.assembleia.pr.leg.br/"
links "https://transparencia.alesc.sc.gov.br/"
links "https://www.al.mt.gov.br/transparencia/"
links "https://al.ms.gov.br/transparencia"
links "https://www.al.ba.gov.br/transparencia"
links "https://www.assembleia.pr.leg.br/" "deput|api|dados"
links "https://www.alesc.sc.gov.br/" "deputad|api|dados"
