set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
links() { echo "### $1"; curl -sSL -A "$ua" --max-time 60 -o /tmp/x -w "== HTTP %{http_code} %{content_type} %{size_download}B\n" "$1"; grep -oiE '(href|src|data-url|action)="[^"#]*"' /tmp/x | sort -u | grep -iE "${2:-csv|json|xls|api|download|dados|ods|xml|arquivo|export}" | head -40; }
raw() { echo "### RAW $1"; curl -sSL -A "$ua" --max-time 60 "$1" | head -c ${2:-1500}; echo; }
for h in transparencia.assembleia.pr.leg.br transparencia.alesc.sc.gov.br www.al.mt.gov.br www.al.ba.gov.br al.ms.gov.br; do raw "https://$h/robots.txt" 600; done
links "https://transparencia.assembleia.pr.leg.br/servicos/dados-abertos"
links "https://transparencia.assembleia.pr.leg.br/receitas-e-despesas/verbas-de-ressarcimento"
links "https://transparencia.assembleia.pr.leg.br/pessoal/parlamentares"
links "https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/dados-abertos"
links "https://transparencia.alesc.sc.gov.br/despesas/dados-abertos"
links "https://transparencia.alesc.sc.gov.br/deputados"
raw "https://api.al.mt.gov.br/" 1500
links "https://www.al.mt.gov.br/parlamento/verba-indenizatoria"
links "https://www.al.mt.gov.br/parlamento/subsidio/"
links "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias"
links "https://al.ms.gov.br/Paginas/202406/ceap-cota-do-exercicio-da-atividade-parlamentar"
