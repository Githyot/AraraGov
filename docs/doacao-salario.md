# Doação do salário

Alguns políticos dizem publicamente que doam o salário, ou parte dele. Não
existe fonte oficial para isso, então o AraraGov mantém uma lista curada em
[`araragov/referencia/doacao_salario.csv`](../araragov/referencia/doacao_salario.csv).

Regras da lista:

- Cada linha precisa de uma fonte pública: fala do próprio político (rede
  social, site do mandato) ou reportagem. Linhas sem link são ignoradas.
- O texto diz o que a pessoa declara ("Declara doar 20% do salário"), sem
  dizer que a doação foi conferida e sem julgar quem não doa.
- Quem não está na lista aparece como "não declarada", não como "não doa".

Colunas (separadas por `;`): `casa` (camara, senado, al-sp…), `nome` (nome
parlamentar, como aparece no app), `parte` (ex.: `20%`, vazio se for o
salário inteiro), `periodo` (ano a que a doação se refere; vazio se a
pessoa diz que doa todo mês), `descricao`, `fonte` (link) e `data` da declaração.

Declarações com período aparecem no passado ("Declarou doar 30% do salário em
2020"), para não sugerir que a doação continua.

No app, o perfil mostra a declaração no grupo Salário, com o link para a
fonte, e a busca tem o filtro "Doa o salário".
