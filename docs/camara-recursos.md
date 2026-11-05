# Câmara: recursos e benefícios de cada deputado

A página pública de cada deputado (`https://www.camara.leg.br/deputados/{id}?ano=AAAA`)
traz, por ano, o que a API de dados abertos não tem. O alvo
`araragov coletar camara-recursos --ano AAAA` lê:

| Dado | Onde aparece no app |
|---|---|
| Verba de gabinete gasta por mês (salários dos secretários parlamentares) | Gabinete: custo mensal e gasto do ano |
| Salário bruto pago em cada mês (`/remuneracao`) | Salário: "Salário bruto pago em AAAA" |
| Imóvel funcional (desde quando) | Salário: benefícios |
| Auxílio-moradia, com o total recebido no ano | Salário: benefícios |
| Viagens em missão oficial | Salário: benefícios |
| Passaporte diplomático | Salário: benefícios |

## O que não coletamos e por quê

- **Salário de cada secretário parlamentar.** A página de remuneração de cada
  funcionário fica em `/transparencia/recursos-humanos/remuneracao/`, que o
  `robots.txt` da Câmara pede para não coletar. O custo do gabinete vem da
  verba de gabinete gasta no mês, que é a soma desses salários. O nível de
  cada pessoa (SP01 a SP25) aparece na lista da equipe.
- **Plano de saúde e reembolsos médicos.** A Câmara não publica esses valores
  por deputado.

A coleta baixa 2 páginas por deputado e ano, com até 4 downloads ao mesmo tempo.
