# Estados

## De onde vêm os dados

| O quê | Fonte | Cobertura |
|---|---|---|
| Governadores, vices e deputados estaduais/distritais eleitos | [TSE, candidatos 2022](https://dadosabertos.tse.jus.br) | 27 estados |
| Deputados em exercício (inclui suplentes que assumiram e partido atual) | [ALMG](https://dadosabertos.almg.gov.br/ws/ajuda/sobre), [Alesp](https://www.al.sp.gov.br/dados-abertos/) | MG, SP |
| Gastos do mandato | ALMG (verbas indenizatórias), Alesp (despesas de gabinete) | MG, SP |

Onde a assembleia tem lista própria, ela substitui a do TSE. Nos outros
estados, o perfil mostra o aviso de que os dados são da eleição de 2022.

O arquivo do TSE traz CPF, título de eleitor e data de nascimento. Esses
campos não são lidos nem gravados.

## Salário

A Constituição (art. 27, § 2º) limita o subsídio do deputado estadual a 75%
do subsídio do deputado federal. O app mostra esse valor como **teto**, porque
cada assembleia fixa o seu por lei. O salário de governadores varia por lei
estadual e ainda não foi coletado.

## Próximos estados

Outras assembleias publicam dados em formatos diferentes. A ALEPE (PE) tem
API, mas estava fora do ar na sondagem de novembro de 2026. Votações nominais
estaduais ainda não têm fonte aberta e uniforme.

## Ids

`al-mg-12193` = Assembleia Legislativa de MG, id da própria ALMG.
`al-ba-13123` = Assembleia da BA, número de urna no TSE.
`gov-mg-300` / `gov-mg-301` = governador / vice de MG (número do partido × 10, +1 para o vice).
