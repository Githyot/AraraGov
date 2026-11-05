set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
dump() { echo "### $1"; curl -sSL -A "$ua" --max-time 90 -o /tmp/p -w "== HTTP %{http_code} %{content_type} %{size_download}B %{url_effective}\n" "$1"; python3 - <<'P'
import re
h=open('/tmp/p',encoding='utf-8',errors='replace').read()
for m in re.findall(r'(?:href|src|action|data-[a-z-]+)="([^"#]+)"',h):
    if re.search(r'verba|indeniz|api|json|csv|xls|ajax|consulta|deputad|ceap|cota|ano=|mes=|download|relat',m,re.I): print('  L',m[:200])
for m in sorted(set(re.findall(r'''(?:fetch|axios\.get|\$\.(?:get|post|ajax)|url\s*:)\s*\(?\s*['"`]([^'"`]+)''',h)))[:30]: print('  JS',m[:200])
t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t)
i=t.lower().find('verba'); print('  TXT',t[max(0,i-200):i+1200] if i>=0 else t[:800])
P
}
dump "https://www.al.mt.gov.br/parlamento/verba-indenizatoria"
dump "https://al.ms.gov.br/Paginas/202406/ceap-cota-do-exercicio-da-atividade-parlamentar"
dump "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias"
dump "https://www.al.ba.gov.br/deputados/legislatura-atual"
