set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
for u in "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias-excel" "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias-excel?ano=2025"; do echo "### $u"; curl -sSL -A "$ua" --max-time 120 -D /tmp/h -o /tmp/x "$u"; grep -iE "^(HTTP|content-)" /tmp/h; ls -l /tmp/x; file /tmp/x; python3 -c "
import openpyxl,sys
try:
  wb=openpyxl.load_workbook('/tmp/x',read_only=True); ws=wb.active
  for i,r in enumerate(ws.iter_rows(values_only=True)):
    print(r)
    if i>12: break
  print('ROWS',ws.max_row)
except Exception as e: print('ERR',e); print(open('/tmp/x','rb').read(600))
"; done
echo "### detalhe"; curl -sSL -A "$ua" --max-time 60 "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias/102781/" | python3 -c "
import sys,re; h=sys.stdin.read(); t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S); i=t.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh])[^>]+>','',t[i:i+6000])))"
echo "### lista 2025"; curl -sSL -A "$ua" --max-time 60 "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias?ano=2025&page=1&size=20" | python3 -c "
import sys,re; h=sys.stdin.read(); i=h.find('<table'); print(re.sub(r'\s+',' ',re.sub(r'<(?!/?t[rdh]|a )[^>]+>','',h[i:i+5000])))"
echo "### MT texto"; curl -sSL -A "$ua" --max-time 60 https://www.al.mt.gov.br/parlamento/verba-indenizatoria | python3 -c "
import sys,re; h=sys.stdin.read(); t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t); i=t.find('A concessão'); print(t[i:i+2500])"
