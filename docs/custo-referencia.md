# Custo de referência de obras e serviços

Para cada obra ou compra municipal, o AraraGov calcula quanto aquilo
"deveria" custar naquele estado e naquela época, e mostra a diferença para o
valor contratado e pago. O objetivo é levantar perguntas com números, não
acusar: preço acima da referência pode ter explicação (terreno, distância,
urgência, especificação melhor), e o app diz isso ao lado.

## O que é comparado

Cada item é medido numa **unidade comum**, para que obras diferentes possam
ser comparadas:

| Tipo | Unidade | Exemplos |
|---|---|---|
| Pavimentação | m² ou km de via (com largura) | asfalto (CBUQ), recape, lajota, paralelepípedo |
| Iluminação | unidade | poste, luminária LED, troca de lâmpada |
| Edificações | m² construído | escola, creche, UBS, hospital, quadra |
| Saneamento | metro | rede de água, esgoto, drenagem |
| Serviços | mês ou unidade | coleta de lixo por tonelada, transporte escolar por km |
| Eventos e cultura | evento, diária, hora | palco, som, show, estrutura |

Quando a fonte não traz a quantidade (m², km, unidades), o item fica sem
comparação e o app diz "quantidade não informada". Não se estima quantidade.

## Os três níveis

O valor de referência sai do **melhor nível disponível**. Cada resultado
guarda o nível usado, para o leitor saber o quanto confiar.

### Nível 1: preço publicado no mesmo estado e ano

Fontes, da mais forte para a mais fraca:

1. **Tabelas oficiais**: SINAPI (Caixa/IBGE, mensal, por estado, usada por lei
   como referência de obras com dinheiro federal) e SICRO (DNIT, para
   estradas e pavimentação).
2. **Preços contratados em outros municípios** do mesmo estado e ano, para o
   mesmo item (PNCP e dados dos TCEs). Usa-se a mediana, nunca o menor preço.
3. **Artigos, estudos e tabelas de empresas** com o valor do m² ou do km no
   estado e no ano, cada um com link e data.

Se houver várias fontes, a faixa vai do menor ao maior valor entre elas
(descartando os extremos quando há pelo menos cinco).

### Nível 2: composição (insumo + frete + mão de obra)

Quando não há preço pronto para o estado e o ano, o custo é montado pelas
partes, com as quantidades da composição SINAPI ou SICRO do serviço:

- **Insumos e commodities** no mês: asfalto (CAP) e diesel pela ANP, aço,
  cimento e brita pelos insumos do SINAPI.
- **Frete**: piso mínimo de frete da ANTT pela distância até o fornecedor
  mais próximo do insumo (refinaria ou distribuidora, no caso do asfalto).
- **Mão de obra e equipamentos**: custos horários do SINAPI/SICRO do estado.
- **BDI** (lucro e despesas indiretas): faixa aceita pelo TCU (Acórdão
  2622/2013) para o tipo de obra.

### Nível 3: dado esticado no tempo ou no espaço

Se nem o nível 2 for possível, o dado do nível 1 é levado para o ano ou
estado que falta:

- **Outro ano, mesmo estado**: corrige pelo índice de custo do setor (SINAPI
  do IBGE para edificações, índices do DNIT para rodovias). O IPCA só entra se
  não houver índice do setor, e o app avisa.
- **Mesmo ano, estado vizinho**: ajusta pela razão entre os custos médios do
  SINAPI dos dois estados.
- Quanto mais longe o dado (em anos ou em distância), mais larga a faixa.

## Períodos atípicos

Alguns períodos mexeram nos preços de forma que a inflação geral não mostra:

| Período | O que aconteceu | Como é tratado |
|---|---|---|
| 2020-2022 | Pandemia: aço, PVC, cobre e asfalto subiram muito acima do IPCA; contratos emergenciais sem licitação | Só índice do setor (nunca IPCA); faixa alargada; aviso "período atípico" |
| 2021-2022 | Alta do petróleo: asfalto e diesel | Nível 2 com preço ANP do mês |
| Calamidades (enchentes, secas) | Decretos de emergência e compras urgentes | Aviso "obra em situação de emergência" quando houver decreto |

Esses períodos ficam numa tabela no banco de referência, com a fonte, e podem
ser ampliados.

## O que o app mostra

Para cada obra:

- Valor contratado, aditivos e valor pago, em reais da época e corrigidos.
- Faixa de referência, com o nível (1, 2 ou 3), as fontes e a data.
- **"Dentro da faixa"**, **"abaixo da faixa"** ou **"X% acima da faixa de
  referência"**. A palavra "superfaturamento" não é usada.

Indicadores de atenção que não dependem de preço (todos com fonte):

- Aditivos acima de 25% do contrato (limite da Lei 14.133, art. 125, e da
  antiga Lei 8.666, art. 65).
- A mesma rua ou o mesmo serviço pago de novo em pouco tempo (recape da mesma
  via em menos de 5 anos).
- Obra paralisada ou pagamento maior que a etapa executada, quando o dado
  existir (Obrasgov, TCE).
- Bem público vendido muito abaixo do valor de compra corrigido.

## Qualidade

Qualidade é o que menos aparece em dado público. O app usa só o que é
documentado: situação da obra (Obrasgov, TCE), refazimento em pouco tempo,
apontamentos e auditorias dos Tribunais de Contas com link. Não há nota de
qualidade inventada.

## Banco de referência

Fica em `v1/referencia/custos/{uf}.md`, no [formato do projeto](formato-md.md),
com uma linha por item, estado e mês: unidade, valor, nível, fonte e link.
Linhas de artigos e de empresas precisam de link; sem link, a linha é
ignorada (mesma regra da lista de doação do salário).
