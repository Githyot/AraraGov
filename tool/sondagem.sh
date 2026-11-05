set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
curl -sSL -A "$ua" --max-time 90 https://portalrh.alba.ba.gov.br/transparencia -o /tmp/t
echo "### ajax"; grep -nE 'ajax|\"data\":|url\s*:|\.get\(|\.post\(|sAjaxSource|fetch\(' /tmp/t | cut -c1-220 | head -40
