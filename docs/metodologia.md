# Metodologia das análises

O AraraGov só organiza dados públicos. As análises abaixo descrevem **como**
cada parlamentar votou. Não acusam ninguém nem dizem o que é certo.

## Posição nas votações (esquerda e direita)

Não classificamos leis à mão. A posição sai dos próprios votos:

1. Pegamos as votações nominais **divididas** (o lado perdedor teve pelo menos
   10% dos votos) de cada casa.
2. Montamos a tabela parlamentar x votação (Sim = +1, Não = −1) e calculamos o
   eixo que mais separa os parlamentares (primeira componente principal, a
   mesma ideia do NOMINATE e do Basômetro). No Congresso brasileiro esse eixo
   corresponde, na prática, à divisão entre esquerda e direita.
3. O sentido do eixo é fixado por três partidos de referência: o lado em que
   ficam PT, PSOL e PCdoB é chamado de esquerda. Essa é a única informação
   externa usada.
4. Cada votação é classificada pelo grupo que votou Sim. Se quem votou Sim
   está, em média, mais à esquerda que quem votou Não, o Sim foi a posição
   mais à esquerda naquela votação. Se os dois grupos se misturam (diferença
   menor que meio desvio-padrão), a votação fica **sem lado claro** e não entra
   na conta.
5. A posição do parlamentar é o percentual dessas votações em que ficou do
   lado da esquerda ou da direita.

Faixas usadas: esquerda (65% ou mais à esquerda), centro-esquerda (55–65%),
centro (45–55%), centro-direita (35–45%) e direita (menos de 35%). Não usamos
rótulos extremistas.

Código: [`araragov/analise/espectro.py`](../araragov/analise/espectro.py).

## Com quem vota junto

Em cada votação, a posição de um partido é a da maioria dos seus membros que
votaram Sim ou Não (empates não contam). O alinhamento com um partido é o
percentual de votações em comum em que o parlamentar votou igual a essa
maioria. Só mostramos partidos com pelo menos 10 votações em comum.

## Votações que merecem atenção

São votações cujo texto trata de assuntos que afetam os próprios
parlamentares. As regras são buscas simples na ementa e na descrição:

- salário, auxílio-moradia, ajuda de custo ou verba de gabinete de parlamentares;
- fundo eleitoral ou fundo partidário;
- emendas parlamentares ao orçamento;
- anistia a partidos ou candidatos;
- imunidade ou foro de parlamentares.

Código: [`araragov/analise/atencao.py`](../araragov/analise/atencao.py).
Sugestões de novas regras são bem-vindas.
