# Metodologia das análises

O AraraGov só organiza dados públicos. As análises abaixo descrevem **como**
cada parlamentar votou. Não acusam ninguém nem dizem o que é certo.

## Posição nas votações (esquerda e direita)

Não classificamos leis à mão. A posição sai dos próprios votos:

1. Usamos dois blocos de referência: **PT, PSOL e PCdoB** (esquerda) e
   **PL e NOVO** (direita). É a única informação externa, e é consenso entre
   pesquisadores.
2. Uma votação é **ideológica** quando a maioria de cada bloco (pelo menos 60%
   dos seus membros que votaram Sim ou Não) ficou de um lado diferente. Nela,
   o Sim recebe o lado do bloco que votou Sim.
3. Votações em que os dois blocos concordam ficam de fora: são consenso e não
   dizem nada sobre o lado de ninguém.
4. A posição do parlamentar é o percentual das votações ideológicas em que ele
   votou com cada lado. Mostramos só quem participou de pelo menos 10.

**Por que não usar só o eixo principal das votações (PCA, NOMINATE)?** No
Congresso brasileiro esse eixo costuma separar governo e oposição, e não
esquerda e direita. Testamos com dados reais de 2025: partidos de centro que
votam com o governo apareciam como "esquerda". Comparar com os dois blocos de
referência evita esse erro.

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
