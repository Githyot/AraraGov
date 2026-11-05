set +e
pip install -q openpyxl xlrd 2>&1 | tail -1
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
get() { for t in 1 2 3 4; do curl -sSL -A "$ua" --max-time 120 -D /tmp/h -o /tmp/x "$1" && return 0; sleep 10; done; }
for u in "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias-excel" "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias-excel?ano=2025"; do echo "### $u"; get "$u"; grep -iE "^(HTTP|content-)" /tmp/h; ls -l /tmp/x; file /tmp/x; python3 -c "
import openpyxl
try:
  wb=openpyxl.load_workbook('/tmp/x',read_only=True); ws=wb.active
  n=0
  for i,r in enumerate(ws.iter_rows(values_only=True)):
    n+=1
    if i<12: print(r)
  print('ROWS',n)
  if n: print('LAST',r)
except Exception as e: print('ERR',e); print(open('/tmp/x','rb').read(400))
"; done
echo "### detalhe script"; get "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias/102781/"; grep -oE '(fetch|ajax|url)[^;]{0,200}' /tmp/x | head; grep -oE '<td[^>]*>[^<]{1,100}' /tmp/x | head -40
