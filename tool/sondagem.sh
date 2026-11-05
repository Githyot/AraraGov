set +e
git fetch -q --depth 1 origin etapa-9-estados && git checkout -q FETCH_HEAD -- araragov pyproject.toml
pip install -q -e . 2>&1 | tail -1
echo "### coleta real"
python -m araragov coletar estados-eleitos 2>&1 | grep -iE "erro|error" | tail -3
python -m araragov coletar alece-deputados 2>&1 | grep -iE "alece|erro|error|Traceback" | cut -c1-600
python -m araragov coletar alece-despesas --ano 2026 2>&1 | grep -iE "ligados" | cut -c1-900
python3 - <<'P'
import sqlite3,glob
db=glob.glob('**/*.db',recursive=True)+glob.glob('**/*.sqlite*',recursive=True); print(db)
c=sqlite3.connect(db[0])
print(c.execute("select fonte,em_exercicio,count(*) from politico where casa='al-ce' group by 1,2").fetchall())
print(c.execute("select nome,nome_civil,partido from politico where casa='al-ce' and fonte='assembleia'").fetchall())
P
