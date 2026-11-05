set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
for u in https://www.alepe.pe.gov.br https://transparencia.alepe.pe.gov.br https://www.al.rs.gov.br https://ww4.al.rs.gov.br https://www.al.es.gov.br https://www3.al.es.gov.br https://www.cl.df.gov.br https://dados.cl.df.gov.br https://www.aleam.gov.br https://transparencia.aleam.gov.br https://www.al.ap.gov.br https://www.al.ma.leg.br https://transparencia.al.ma.leg.br https://www.alepi.pi.gov.br https://alepi.pi.gov.br https://transparencia.alepi.pi.gov.br https://www.al.pb.leg.br https://transparencia.al.pb.leg.br https://al.rr.leg.br https://transparencia.al.rr.leg.br https://www.al.ac.leg.br https://www.al.al.leg.br https://transparencia.al.al.leg.br https://www.aleac.ac.gov.br; do
  r=$(curl -sSL -A "$ua" --max-time 25 -o /tmp/p -w "%{http_code} %{url_effective}" "$u" 2>&1 | tail -1 | cut -c1-140); echo "### $u -> $r $(wc -c </tmp/p 2>/dev/null)"
  grep -oiE 'href="[^"#]*(transparen|verba|indeniz|cota|ceap|gabinete|dados-?abertos|despesa)[^"]*"' /tmp/p 2>/dev/null | sort -u | head -8
  rm -f /tmp/p
done
