set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 90 https://portalrh.alba.ba.gov.br/transparencia -o /tmp/t
echo "### js"; sed -n '540,612p' /tmp/t | cut -c1-200
