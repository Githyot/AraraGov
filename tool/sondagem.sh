set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
U=https://transparencia.al.rr.leg.br/execucao-orcamentaria-e-financeira/verbas-indenizatorias-a-partir-de-set25/
curl -sSL -A "$ua" --max-time 40 -c /tmp/ck $U -o /tmp/r
n=$(grep -oE '"wpdf_nonce":"[^"]*' /tmp/r | cut -d'"' -f4); id=$(grep -oE 'wpdf-[0-9]+' /tmp/r | head -1 | cut -d- -f2)
echo "### RR ajax nonce=$n id=$id"; curl -sS -A "$ua" -b /tmp/ck --max-time 40 https://transparencia.al.rr.leg.br/wp-content/plugins/wp-display-files/assets/js/wpdf-custom.js | grep -oE "action\s*:\s*['\"][a-z_]+['\"][^}]{0,200}" | head -5
for a in wpdf_get_folder_listing get_listing wpdf_listing; do curl -sS -A "$ua" -b /tmp/ck --max-time 40 -d "action=$a&path=Ano 2026/&folder=Ano 2026&nonce=$n&security=$n&id=$id" https://transparencia.al.rr.leg.br/wp-admin/admin-ajax.php | head -c 400; echo " <- $a"; done
echo "### PB remuneracoes"; curl -sSL -A "$ua" --max-time 40 https://www.al.pb.leg.br/transparencia/recursos-humanos/remuneracoes -o /tmp/p; grep -oiE '(href|src)="[^"#]*"' /tmp/p | grep -iE "pdf|xls|csv|ods|json|uploads/20|sagres|tce" | sort -u | head -12
