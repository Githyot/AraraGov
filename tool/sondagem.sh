set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
p() { echo "### $1"; curl -sSL -A "$ua" --connect-timeout 30 --max-time 90 -o /tmp/p -w "== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$1"; grep -oiE 'href="[^"#]*"' /tmp/p | sort -u | grep -iE "verba|indeniz|despes|dados|csv|json|xls|api|cota|deputad" | head -25; }
p "https://dadosabertos.alepe.pe.gov.br/"
p "https://dadosabertos.alepe.pe.gov.br/api/v1/parlamentares"
p "https://www.alepe.pe.gov.br/transparencia/"
p "https://ww4.al.rs.gov.br/transparencia"
p "https://www.al.rs.gov.br/"
p "https://www.al.es.gov.br/Transparencia"
p "https://www.alerj.rj.gov.br/Transparencia"
p "https://transparencia.alerj.rj.gov.br/"
p "https://www.cl.df.gov.br/transparencia"
p "https://www.almg.gov.br/robots.txt"
