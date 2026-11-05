set +e
ua="AraraGov/0.1 (+https://github.com/Githyot/AraraGov)"
for id in 204536 160976 62881; do
  curl -sSL -A "$ua" --max-time 120 -o /tmp/d.html "https://www.camara.leg.br/deputados/$id?ano=2025"
  echo "=====PRINCIPAL $id"
  python3 -c "
t=open('/tmp/d.html',encoding='utf-8').read()
a=t.find('Gastos e recursos'); b=t.find('Agenda do Deputado')
print(t[a-300:b])" | gzip -9 | base64 -w0; echo
done
curl -sSL -A "$ua" --max-time 120 -o /tmp/r.html "https://www.camara.leg.br/deputados/204536/remuneracao?ano=2025"
echo "=====REMUNERACAO"
python3 -c "
t=open('/tmp/r.html',encoding='utf-8').read()
a=t.find('<main'); b=t.find('</main>')
print(t[a:b+7] if a>=0 else t)" | gzip -9 | base64 -w0; echo
curl -sSL -A "$ua" --max-time 120 -o /tmp/p.html "https://www.camara.leg.br/deputados/204536/pessoal-gabinete?ano=2025"
echo "=====PESSOAL"
python3 -c "
t=open('/tmp/p.html',encoding='utf-8').read()
a=t.find('<main'); b=t.find('</main>')
print(t[a:b+7] if a>=0 else t)" | gzip -9 | base64 -w0; echo
echo "=====FIM"
