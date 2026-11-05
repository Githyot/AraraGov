# Estados

O AraraGov só usa dados que os estados já publicam. Não fazemos pedidos ao
governo e respeitamos o robots.txt de cada portal.

## Quem aparece

A base é a lista de eleitos do TSE nos 27 estados (governador, vice e
deputados estaduais). Onde a assembleia publica a própria lista (MG e SP),
ela substitui a do TSE, porque inclui suplentes em exercício.

Em SC e na BA, a lista de deputados em exercício publicada pela assembleia
é cruzada com a do TSE:

- quem está nas duas fica em exercício, com aviso de que o partido é o da
  eleição de 2022;
- suplente que assumiu ganha perfil próprio (código 1.000.000 + id da
  assembleia), sem partido, porque a assembleia não o publica;
- eleito que não aparece na lista oficial fica fora de exercício.

## Gastos por assembleia

| UF | Fonte | O que vem |
|---|---|---|
| MG | API de dados abertos da ALMG | verbas indenizatórias por deputado e mês |
| SP | XML de dados abertos da Alesp | despesas de gabinete por deputado e mês |
| BA | planilha anual da ALBA (`/transparencia/verbas-idenizatorias-excel?ano=`) | verbas indenizatórias por deputado: processo, nota, data, categoria e valor (sem fornecedor) |
| SC | CSV anual da Alesc (`/gabinetes-parlamentares/csv/{ano}`, desde 2011) | diárias, passagens, telefone, escritório de apoio, combustível etc. |

Na Alesc, a planilha traz o nome do deputado como a assembleia escreve
("Ana Paula da Silva (Paulinha)"). O coletor liga o gasto ao deputado do TSE
pelo nome de urna ou civil, e só quando há um único candidato. Gastos de quem
não foi ligado (suplentes, ex-deputados) ficam com o nome, sem perfil. O log
da coleta lista esses nomes.

### Assembleias estudadas e ainda fora

- **PR (Alep):** gastos de ressarcimento só aparecem em telas e numa API
  interna que o robots.txt fecha. A API aberta (`webservices.assembleia.pr.leg.br/api/public`)
  só tem proposições e normas.
- **MT, MS:** o site não publica os gastos de cada deputado.
- **PE, RS, ES, DF:** os portais não responderam a acessos de fora do Brasil
  (onde roda a coleta). Vamos tentar de novo.
- **RJ:** os gastos ficam no sistema DOCIGP da Alerj, e o robots.txt dele fecha o site inteiro, então não coletamos.

## Gabinetes

- **SC:** a página de servidores da Alesc filtra por lotação ("GAB DEP X").
  Coletamos nome e vínculo de cada pessoa. A remuneração só aparece na tela de
  contracheque, que o robots.txt fecha, então o app mostra "Sem dados" para o
  salário da equipe, com a Alesc como responsável.

## Votações

Nenhuma assembleia que responde publica o voto de cada deputado em arquivo
aberto. A Alep tem uma rota de votações, mas dentro de /api/, que o robots.txt
fecha. A Alesp publica só a presença.

## Salário

O arquivo `araragov/referencia/subsidios_estaduais.csv` guarda o salário por
estado e cargo, com a fonte de cada valor:

- `tipo=lei`: valor tirado da lei estadual (SC, SP e GO para deputados; SP
  para governador e vice).
- `tipo=oficial`: valor publicado pelo próprio órgão, sem a lei nem a data de início (RJ).
- `tipo=imprensa`: valor publicado pela imprensa enquanto a lei não foi
  conferida (governadores, levantamento do Valor Econômico de outubro de 2026).
  O app avisa que é valor da imprensa.

Linhas sem link de fonte são ignoradas. Estados sem linha para deputados
continuam mostrando o teto constitucional (75% do deputado federal).

## Quando falta dado

Toda seção sem dado mostra "Sem dados" e o órgão responsável por publicar
aquele dado, com a esfera (por exemplo, "Assembleia Legislativa (MT), esfera
estadual" ou "Câmara dos Deputados, esfera federal"). O app não diz o motivo
da falta: pode ser que o órgão não publique, ou que o AraraGov ainda não
colete aquela fonte. Governador e vice não têm a seção de votações, porque
não votam em plenário.
