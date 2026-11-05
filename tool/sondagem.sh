set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
p() { echo "### $1"; curl -sSL -A "$ua" --max-time 40 -H "Accept: application/json, text/html;q=0.8" -o /tmp/x -w "== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$1"; head -c ${2:-500} /tmp/x | tr '\n' ' '; echo; }
for e in parlamentares remuneracao servidores; do p "https://dadosabertos.alepe.pe.gov.br/$e" 800; done
p "https://dadosabertos.alepe.pe.gov.br/" 1500
p "https://dadosabertos.cl.df.gov.br/api/3/action/package_list" 1500
p "https://dadosabertos.cl.df.gov.br/" 600
p "https://ww4.al.rs.gov.br/dadosabertos" 600
p "https://dadosabertos.al.rs.gov.br/" 600
p "https://www.al.rs.gov.br/transparencia" 300
p "https://www.assembleia.pr.leg.br/transparencia" 300
p "https://transparencia.assembleia.pr.leg.br/" 600
p "https://www.alesc.sc.gov.br/dados-abertos" 600
p "https://transparencia.alesc.sc.gov.br/" 400
p "https://www.alerj.rj.gov.br/Transparencia" 300
p "https://dadosabertos.alerj.rj.gov.br/" 400
p "https://www.al.ce.gov.br/dados-abertos" 400
p "https://www.al.ba.gov.br/transparencia" 300
p "https://portal.al.go.leg.br/dados-abertos" 400
p "https://www.al.mt.gov.br/transparencia" 300
p "https://www.al.ms.gov.br/transparencia" 300
p "https://www.al.es.gov.br/Transparencia" 300
p "https://dados.al.es.gov.br/" 400
