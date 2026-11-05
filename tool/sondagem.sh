set +e
pip install -q openpyxl 2>&1 | tail -1
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
get() { for t in 1 2 3 4; do curl -sSL -A "$ua" --max-time 120 -o "$2" "$1" && return 0; sleep 10; done; }
for a in 2025 2019; do echo "### $a"; get "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias-excel?ano=$a" /tmp/v$a.xlsx; python3 -c "
import openpyxl,collections
wb=openpyxl.load_workbook('/tmp/v$a.xlsx'); print(wb.sheetnames); ws=wb.active
rows=list(ws.iter_rows(values_only=True)); print('ROWS',len(rows))
for r in rows[:8]: print(r)
print('LAST',rows[-1])
hdr=None
for i,r in enumerate(rows):
  if r and any(isinstance(c,str) and 'eputad' in c for c in r): hdr=i; print('HDR',i,r); break
if hdr is not None:
  for j,c in enumerate(rows[hdr]):
    vals=collections.Counter(str(x[j])[:40] for x in rows[hdr+1:] if x and len(x)>j)
    print('COL',j,c,len(vals),vals.most_common(6))
"; done
cp /tmp/v2025.xlsx /tmp/alba.xlsx; base64 -w0 /tmp/alba.xlsx | head -c 0
