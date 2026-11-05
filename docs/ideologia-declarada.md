# Ideologia declarada

O app mostra a posição de cada político medida pelos votos (ver
`docs/metodologia.md`). Ao lado, mostra o que o partido, ou a própria pessoa,
diz sobre a sua ideologia, **nas palavras deles**, com a fonte. O app não
compara nem julga: só põe as duas informações lado a lado.

Listas curadas:

- [`araragov/referencia/ideologia_partidos.csv`](../araragov/referencia/ideologia_partidos.csv):
  `partido;declaracao;trecho;documento;fonte`
- [`araragov/referencia/ideologia_politicos.csv`](../araragov/referencia/ideologia_politicos.csv):
  `casa;nome;declaracao;trecho;documento;fonte`

Regras:

- Só entra o que o próprio partido ou político declara: estatuto, programa,
  carta oficial, perfil nas redes ou entrevista. Rótulos dados por terceiros
  (imprensa, Wikipédia, adversários) não entram.
- O `trecho` é uma citação literal da fonte; `declaracao` é o termo usado por
  eles (por exemplo "socialismo democrático", "comunismo", "liberal",
  "anarcocapitalista", "conservador").
- Linhas sem link de fonte são ignoradas.

Partidos conferidos até agora: PT, PCdoB, PDT e PL. Os demais entram à
medida que a declaração for encontrada em documento do próprio partido.
