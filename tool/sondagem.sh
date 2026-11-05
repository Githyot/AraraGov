set +e
git fetch -q --depth 1 origin etapa-9-estados && git checkout -q FETCH_HEAD -- araragov pyproject.toml
pip install -q -e . 2>&1 | tail -1
echo "### coleta real"
python -m araragov coletar estados-eleitos 2>&1 | grep -iE "erro|error|eleitos|grav" | tail -3
for a in alece-despesas alepa-gabinetes alero-gabinetes; do echo "## $a"; python -m araragov -v coletar $a --ano 2026 2>&1 | grep -iE "alece|alepa|ale-ro|erro|error|traceback|exception|^despesa|^assessor" | grep -v "GET http" | tail -6 | cut -c1-1500; done
