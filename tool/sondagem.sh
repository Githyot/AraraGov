set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
U=https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/
curl -sSL -A "$ua" --max-time 40 -c /tmp/ck $U -o /tmp/r
n=$(grep -oE '"wpdf_nonce":"[^"]*' /tmp/r | cut -d'"' -f4)
echo "### js"; curl -sS -A "$ua" --max-time 40 https://transparencia.al.rr.leg.br/wp-content/plugins/wp-display-files/assets/js/wpdf-custom.js | grep -oE "wpdf_load_folder_data.{0,400}" | head -2
echo "### RR ajax"; curl -sS -A "$ua" -b /tmp/ck --max-time 40 --data-urlencode "action=wpdf_load_folder_data" --data-urlencode "path=Ano 2026/" --data-urlencode "folder=Ano 2026/" --data-urlencode "nonce=$n" --data-urlencode "wpdf_nonce=$n" --data-urlencode "id=9" --data-urlencode "post_id=9" https://transparencia.al.rr.leg.br/wp-admin/admin-ajax.php | grep -oE '(data-name|href)="[^"]*"' | head -15
