# Municípios: plano

A fase municipal é a mais difícil e a mais importante. São 5.570 prefeituras,
cada uma com um portal próprio, e é nelas que obras superfaturadas e desvio de
dinheiro costumam passar despercebidos.

O AraraGov **não acusa ninguém**. Ele junta dados públicos, compara com
referências públicas e mostra onde os números fogem do esperado, sempre com a
fonte e uma ressalva. Quem conclui é o leitor, a imprensa, o Ministério
Público e o Tribunal de Contas.

## O que o app vai mostrar de cada município

1. **Quem governa e governou**: prefeito, vice e vereadores de cada mandato
   (2017-2020, 2021-2024, 2025-2028), com partido e foto do TSE.
2. **Salários**: subsídio de prefeito, vice, secretários e vereadores (lei
   municipal) e a folha da câmara e da prefeitura quando publicada.
3. **Arrecadação**: quanto entrou por tipo (IPTU, ISS, ITBI, FPM, ICMS, SUS,
   Fundeb, emendas, convênios), por ano, corrigido pelo IPCA.
4. **Gastos por área**: saúde, educação, urbanismo, transporte, assistência,
   cultura etc. Cada área abre em subáreas e depois nos pagamentos: quem
   recebeu, quanto, quando, por qual contrato.
5. **Obras**: cada obra com valor contratado, aditivos, valor pago, situação
   (em andamento, concluída, paralisada) e o **custo de referência** para o
   mesmo serviço naquele estado e ano (veja [custo-referencia.md](custo-referencia.md)).
6. **Fornecedores (CNPJs)**: os que mais receberam em cada ano, com quem
   governava na época, sócios (dados públicos da Receita) e indícios
   documentados de vínculo (veja "Vínculos" abaixo).
7. **Emendas e transferências**: emendas parlamentares e transferências
   federais e estaduais que chegaram ao município, de quem vieram e em quem
   foram gastas.
8. **Venda e baixa de bens**: leilões e alienações comparados com o valor de
   compra (caso real: [postes de R$ 4,5 milhões vendidos como sucata por
   R$ 555 mil em Campo Mourão](https://www.tribunadointerior.com.br/campo-mourao/postes-que-custaram-r-45-milhoes-sao-vendidos-como-sucata-por-r-555-mil-em-campo-mourao/)).

## Fontes

A regra é: primeiro a fonte nacional e uniforme, depois o Tribunal de Contas
do estado (que já recebe os dados de todos os municípios), e só por último o
portal de cada prefeitura.

| Dado | Fonte | Cobertura |
|---|---|---|
| Prefeitos, vices, vereadores, partido, foto | TSE, dados abertos (candidatos e eleitos 2016, 2020, 2024) | Brasil |
| Doações e fornecedores de campanha | TSE, prestação de contas eleitorais | Brasil |
| Arrecadação e gastos por função e subfunção | Tesouro Nacional, Siconfi (DCA anual, RREO bimestral, MSC mensal); FINBRA para anos antigos | Brasil (quem entrega) |
| Empenhos, liquidações e pagamentos com o favorecido | Dados abertos dos TCEs: TCE-SP, TCE-RS (LicitaCon), TCE-PR, TCE-MG, TCE-PE (Tome Conta), TCE-CE, TCM-BA, TCM-GO, entre outros | Estado inteiro, de uma vez |
| Licitações e contratos | PNCP (Portal Nacional de Contratações Públicas, obrigatório pela Lei 14.133) | Brasil, sobretudo a partir de 2023 |
| Gastos detalhados onde o TCE não publica | Portais padrão das prefeituras: Fiorilli, Betha, IPM, Elotech, GovBR e similares | Por fornecedor de sistema |
| Obras com dinheiro federal | Obrasgov.br (Cadastro Integrado de Projetos de Investimento), Transferegov | Brasil |
| Emendas e "emendas Pix" (transferências especiais) | Portal da Transparência e Transferegov | Brasil |
| Sócios dos CNPJs | Receita Federal, dados abertos do CNPJ (QSA) | Brasil |
| Empresas punidas | CEIS e CNEP (Portal da Transparência) | Brasil |
| Custo de referência de obras | SINAPI (Caixa/IBGE), SICRO (DNIT), índices de custo, ANP (asfalto e diesel), ANTT (frete) | Por estado e mês |
| Inflação | IPCA (BCB SGS 433), já usado no federal | Brasil |

Os portais municipais variam muito, então a coleta deles vem depois e por
fornecedor de sistema: um coletor para Betha serve para todas as prefeituras
que usam Betha.

## Vínculos entre fornecedores e governo

Este é o ponto mais delicado. A Lei Geral de Proteção de Dados (LGPD) e o
princípio de não acusar valem aqui com força total.

**O que o app mostra (indícios documentados, cada um com a fonte):**

- Empresa que **doou** ou **prestou serviço** à campanha do prefeito ou de um
  vereador e depois recebeu do município (TSE + pagamentos).
- Sócio da empresa que **foi candidato** no mesmo município (TSE, nome
  completo igual e mesmo município).
- Sócio da empresa que aparece como **servidor ou comissionado** do município
  (folha publicada, nome completo igual).
- Empresas **com sócio em comum** ou **no mesmo endereço** disputando a mesma
  licitação ou recebendo do mesmo órgão (dados de CNPJ, não de pessoas).
- Empresa **aberta pouco antes** do primeiro contrato, com **capital social
  muito menor** que o contrato, ou com atividade (CNAE) que não combina com o
  que vendeu.
- Empresa no **CEIS/CNEP** (punida) que continuou recebendo.

**Coincidência de sobrenome** aparece só como "sobrenome em comum com o
prefeito/vereador", nunca como "parente". Sobrenomes comuns (Silva, Santos,
Oliveira, Souza e outros acima de um limite de frequência no estado) não
geram aviso. O texto sempre diz que sobrenome igual não prova parentesco.

**O que o app não faz:**

- Não mostra CPF completo de ninguém. A Receita já publica o CPF do sócio
  mascarado (`***123456**`) e o AraraGov mantém assim; o TSE publica CPF e o
  AraraGov não lê esse campo, como já é feito nos estados.
- Não infere parentesco ou amizade sem um dado público que diga isso.
- Não segue dinheiro depois que ele sai do município para a empresa. A
  cadeia "emenda → empresa → outra empresa → laranja" não aparece em dado
  público; o app mostra até onde os dados chegam (emenda → município →
  empenho → CNPJ → sócios) e diz onde a trilha para.
- Não usa pontuação de risco nem ranking de "corruptos".

## Quando não há dado

Em qualquer tela (municipal, estadual ou federal), se um dado não existe o app
mostra **"Não há dados"** e quem deveria tê-lo publicado: a esfera (federal,
estadual ou municipal), o órgão, o que faltou, a lei que manda publicar e a
data em que a fonte foi consultada. Nunca mostra zero no lugar de "sem dado".
O formato está em [formato-md.md](formato-md.md#quando-não-há-dado).

Exemplo: "Não há dados de gastos por área em 2024. Responsável: Prefeitura de
Exemplo (municipal), que não entregou a declaração anual ao Tesouro (Siconfi),
como manda a Lei de Responsabilidade Fiscal, art. 51. Consultado em 5/11/2026."

## Formato dos dados

Os dados municipais saem em arquivos `.md` com um formato fixo, que uma
pessoa lê no navegador e o app lê sem bibliotecas extras. O formato está em
[formato-md.md](formato-md.md). O app baixa só o arquivo do município aberto,
então o tamanho do app não cresce com a base.

Os arquivos de cada município ficam em:

```
v1/municipios/indice.md                 lista de municípios com dados
v1/municipios/{uf}/{ibge}/resumo.md     governo, salários, totais por ano
v1/municipios/{uf}/{ibge}/{ano}.md      arrecadação, gastos por área, maiores pagamentos
v1/municipios/{uf}/{ibge}/obras.md      obras e comparação com a referência
v1/municipios/{uf}/{ibge}/fornecedores.md  CNPJs, sócios e indícios
v1/referencia/custos/{uf}.md            banco de custos de referência do estado
```

O GitHub Pages tem limite de 1 GB. Todos os pagamentos de 5.570 municípios
não cabem nele, então os arquivos guardam os totais e os maiores itens de
cada área, e o resto fica com link para a fonte. Se a base crescer além
disso, os arquivos de municípios vão para um repositório de dados separado.

## Fases (um PR por fase)

| Fase | Entrega | Situação |
|---|---|---|
| 0 | Este plano, o formato `.md` (leitor e escritor) e a metodologia de custo de referência | 🔄 |
| 1 | Quem governa: prefeitos, vices e vereadores 2016/2020/2024 (TSE), por município e período | 🔄 |
| 2 | Arrecadação e gastos por área (Siconfi), Brasil inteiro, com IPCA | 🔄 |
| 3 | Banco de custos de referência (SINAPI, SICRO, índices, ANP, ANTT, artigos) | 🔄 |
| 4 | Estado piloto (SP): pagamentos, contratos e obras pelo TCE-SP, com comparação de custo | 🔄 |
| 5 | Fornecedores: CNPJs, sócios (Receita), CEIS/CNEP e indícios de vínculo | 🔄 |
| 6 | Emendas e transferências até o CNPJ que recebeu | 🔄 |
| 7 | Telas do app (município, área, obra, fornecedor) | 🔄 |
| 8 | Outros estados: contratos pelo PNCP (Brasil inteiro); depois TCEs e portais Fiorilli, Betha, IPM | 🔄 |

**Estado piloto: São Paulo.** O plano sugeria o Paraná, mas o portal de
dados abertos do TCE-PR não respondeu a partir do GitHub (nem o do TCE-RS).
O TCE-SP responde e publica de uma vez os 644 municípios do estado (menos a
capital, que tem tribunal próprio). O Paraná volta na fase 8.

## Fase 1: quem governa

`araragov municipios --saida site` baixa os arquivos de candidaturas do TSE
de 2016, 2020 e 2024 e grava `resumo.md` de cada município (tabela
`mandatos`: eleição, início e fim do mandato, cargo, nome de urna, nome civil,
número, partido, gênero e situação) e o `indice.md` com o prefeito atual e o
número de vereadores. Roda na coleta semanal, depois da exportação.

- O TSE usa código próprio de município. A ligação com o código do IBGE é
  feita pelo nome dentro do estado; os que não batem aparecem no log da
  coleta e são corrigidos em `araragov/referencia/municipios_tse_ibge.csv`.
- O vice entra quando a chapa dele (mesmo número no mesmo município) elegeu o
  prefeito, porque a linha do vice nem sempre diz "eleito".
- Ainda não entram: eleições suplementares, suplentes que assumiram,
  cassações e fotos. O `sq_candidato` e o `cd_eleicao` já ficam gravados para
  ligar a foto e a prestação de contas nas próximas fases.

## Fase 2: arrecadação e gastos por área

`araragov municipios --financas 2019-2025` grava `{ano}.md` de cada
município com o que vem da Declaração de Contas Anuais (DCA) no Siconfi:

- `destaques`: IPTU, ISS, ITBI, FPM, cota de ICMS e IPVA, Fundeb e SUS.
- `receitas`: receita bruta, deduções e líquida por conta (até o 6º nível do
  código; principal, multa e juros ficam somados).
- `areas`: empenhado, liquidado e pago por função (saúde, educação…) e
  subfunção (atenção básica, ensino fundamental…). A despesa
  intraorçamentária (de um órgão do município para outro) é somada.
- No cabeçalho, `ipca_fator` leva os valores de dezembro do ano até o último
  IPCA (`ipca_ate`), para comparar anos.
- Se a DCA não está no Siconfi depois de 30 de abril do ano seguinte, a
  tabela `sem-dados` aponta a prefeitura como responsável (LRF, art. 51).
  Antes do prazo, diz só que a entrega ainda está no prazo.

São 5.570 municípios e dois pedidos por ano. A coleta semanal busca no
máximo 4.000 pares município-ano no Siconfi, sempre refaz os dois últimos
anos (a prefeitura pode retificar) e reaproveita do site publicado os anos
fechados que já têm dados. A base completa de 2019 em diante se forma em
algumas semanas.

O detalhe abaixo da subfunção (cada pagamento, quem recebeu) não está no
Siconfi e vem na fase 4, pelos Tribunais de Contas.

## Fase 4: pagamentos, contratos e obras (SP)

`araragov tce-sp --anos 2024-2025` lê os dados abertos do TCE-SP e grava, por
município:

- `{ano}-pagamentos.md`: só o que foi pago (não o empenhado). Tabelas
  `resumo` (empresas, pessoas físicas e pessoal/dívida), `favorecidos` (as 50
  empresas e entidades que mais receberam, com as áreas),
  `areas-favorecidos` (as 10 maiores de cada subfunção) e `obras` (elemento
  4.4.90.51, obras e instalações, com o histórico do empenho). Pagamento a
  pessoa física aparece só como total e quantidade, sem nome nem CPF. Folha,
  encargos e dívida ficam fora do ranking.
- `{ano}-contratos.md`: `obras` (contratos cujo objeto é obra de um item do
  catálogo de custos, com o valor por m², metro ou unidade comparado com a
  faixa de `v1/referencia/custos/sp.md`), `contratos` (os 60 maiores) e
  `contratacoes-diretas` (empresas com 3 ou mais dispensas ou
  inexigibilidades no ano).

A comparação é feita só quando faz sentido:

- Prédios (escola, creche, UBS, hospital) só contam como obra nova ou
  ampliação. Reforma, pintura, piso, vidro e manutenção ficam de fora, porque
  não se comparam com o custo do m² de um prédio inteiro.
- Sem quantidade ou unidade no contrato: "Quantidade não informada".
- Quantidade 1 (contrato por preço global, comum em iluminação): sem
  comparação.
- Valor por unidade mais de 10 vezes acima ou abaixo da faixa (por exemplo,
  uma escola inteira lançada como "1 m²"): "Quantidade ou unidade incoerente",
  sem comparação. Isso é quase sempre erro de cadastro, não preço.

Quando o item não tem faixa publicada (o preço por serviço do SINAPI ainda
falta), a faixa vem dos próprios contratos: do 1º ao 3º quartil do valor por
unidade em pelo menos 10 contratos de municípios de SP no mesmo ano (nível 1,
"preços contratados em outros municípios").

## Fase 5: fornecedores

`araragov fornecedores --ufs SP` grava `fornecedores.md` de cada município
com as empresas das fases anteriores (pagamentos e contratos) e só fatos com
fonte pública:

- `fornecedores`: total pago, anos, número e valor de contratos e a coluna
  `indicios` ("Sanção no CEIS", "Fornecedora de campanha (2024)"). As
  empresas com indício aparecem primeiro, seguidas das 100 maiores.
- `sancoes`: registros do CEIS e do CNEP (CGU) da empresa, com órgão, estado,
  abrangência, período e fundamento. Pessoas físicas não são lidas.
- `campanha`: serviços que a empresa prestou a candidatos do mesmo município,
  declarados por eles ao TSE (despesas contratadas), com o valor e se o
  candidato foi eleito (pelo `resumo.md` da fase 1). Só eleições ordinárias.
  Empresas que serviram a campanhas em mais de 15 municípios (redes sociais,
  telefonia) ficam fora do cruzamento, porque ele não diria nada.
- `sem-dados`: os sócios e endereços (base de CNPJ da Receita Federal) ainda
  não entram, porque o servidor não responde à coleta automática. Sem eles,
  não há cruzamento de sócio com político, nem de sobrenome.

## Fase 6: emendas

`araragov emendas-municipios` grava `emendas.md` de cada município do Brasil
com as emendas federais pagas a quem está ali, pelo arquivo único de emendas
do Portal da Transparência:

- `resumo`: por ano, número de emendas e de autores, total, quanto foi para o
  governo municipal (prefeitura e fundos municipais) e quanto para entidades
  e empresas.
- `autores`: quem mandou, por tipo de emenda.
- `recebido`: as 300 maiores linhas de ano, emenda, autor, função (saúde,
  cultura…), ação e favorecido com CNPJ. Pessoas físicas aparecem somadas, sem
  nome.
- `sem-dados`: quando o dinheiro vai para a prefeitura, os dados abertos não
  dizem quais empresas ela pagou com ele (responsável: a prefeitura;
  rastreabilidade exigida pelo STF na ADPF 854).

Em `fornecedores.md`, a empresa que recebeu emenda direto e também vendeu à
prefeitura ganha o indício "Recebeu emenda federal direto (autor, ano)".

## Fase 7: telas do app

O botão "Municípios" no topo da tela inicial abre a busca (pelo
`indice.md`). Cada município tem cinco abas, todas lidas direto dos `.md`:

- **Quem governa**: prefeito, vice e vereadores por mandato.
- **Dinheiro**: arrecadação e gastos por área do ano escolhido; cada área
  abre as subáreas e, em SP, quem recebeu em cada uma.
- **Obras**: contratos de obra com o valor por unidade, a faixa de
  referência e a etiqueta "X% acima", "Na faixa", "Abaixo" ou "Sem
  comparação"; obras pagas e contratações diretas repetidas.
- **Fornecedores**: empresas, indícios com fonte, sanções e campanhas.
- **Emendas**: por ano, por autor e por favorecido.

Arquivo que não existe vira "Não há dados" com o motivo; a tabela
`sem-dados` mostra quem deveria ter publicado.

## Fase 8: outros estados

Dos tribunais de contas sondados a partir do GitHub, só TCE-CE, TCE-PB e
TCE-GO responderam; TCE-PR, TCE-MG, TCE-PE, TCE-RS, TCM-BA, TCE-SC e TCE-ES
não. Por isso o primeiro passo é nacional: o **PNCP**, onde todo órgão que
contrata pela Lei 14.133 publica os contratos.

`araragov pncp --anos 2025-2026` grava `{ano}-contratos.md` de cada município
fora de SP, no mesmo formato da fase 4:

- `contratos`: os maiores do ano, com a emenda parlamentar quando o contrato
  informa e o número de controle do PNCP.
- `obras`: objeto classificado no catálogo de custos; a quantidade vem dos
  itens da compra no PNCP (no máximo 3.000 consultas de itens por coleta).
- `contratacoes-diretas`: empresas com 3 ou mais dispensas ou
  inexigibilidades no ano.
- `sem-dados`: contratos pela lei antiga e de quem não publica no PNCP ficam
  de fora (responsável: a prefeitura; Lei 14.133, art. 94 e 174).

Com isso, `fornecedores.md` passa a existir para todos os estados (sanções,
campanhas e emendas).

### Ceará (TCE-CE)

`araragov tce-ce --anos 2025-2026` lê a API do SIM
(`api-dados-abertos.tce.ce.gov.br/sim`) município a município: as notas de
empenho (CNPJ, função, elemento e histórico) e as notas de pagamento, ligadas
pelo empenho. O resultado é `{ano}-pagamentos.md` no mesmo formato de SP, e
os fornecedores do Ceará passam a ter o valor pago.

- O TCE-CE já entrega o documento de pessoa física cifrado; pessoas físicas
  entram só no total, como em SP.
- Contam os pagamentos feitos nos meses do próprio exercício do empenho; restos
  a pagar pagos no ano seguinte ficam de fora.
- A API dá o código da subfunção, não o nome; o app mostra "Subfunção 451".

### Paraíba (TCE-PB)

`araragov tce-pb --anos 2025-2026` baixa o arquivo anual de despesas de todos
os municípios do Sagres
(`download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-AAAA.zip`,
~190 MB) e grava `{ano}-pagamentos.md` como em SP. Cada linha é um empenho com
o valor pago acumulado. O arquivo traz o CPF completo (com zeros à esquerda);
ele é reconhecido pelo dígito verificador do CNPJ e nunca é gravado.
- Outros tribunais sondados em 2026-11-05:
  - TCE-RJ (`dados.tcerj.tc.br/api/v1`): `araragov tce-rj` grava
    `{ano}-contratos.md` dos 91 municípios (a capital fica no PNCP), com CNPJ e
    valor pago por contrato. Sem quantidade, as obras não têm comparação de
    custo, e o arquivo diz isso em `sem-dados`.
  - TCE-RN (`apidadosabertos.tce.rn.gov.br`): incompleto. Mossoró tem 2
    contratos em 2024 e nenhum empenho; Acari tem empenhos (credor e valor
    empenhado, sem elemento da despesa nem valor pago). Sem o elemento não dá
    para separar a folha, então o RN fica no PNCP por enquanto.
  - TCE-PI: só os 10 maiores credores de cada prefeitura, sem CNPJ.
  - TCE-MT, TCE-AL e o portal do TCE-TO não resolveram no GitHub; TCE-MS e
    TCE-AM só têm páginas, sem dados abertos de despesa municipal.
- Goiás: quem fiscaliza os municípios é o TCM-GO, que não respondeu; o TCE-GO
  só tem dados do estado.

## Limitações conhecidas

- Muitos municípios atrasam ou não entregam dados ao Siconfi; o app mostra
  "Não há dados" com o responsável, em vez de zero.
- A ligação entre pagamento e obra nem sempre está no dado: às vezes só o
  número do contrato liga os dois.
- Custo de referência é uma faixa, não um preço exato. Terreno, distância,
  quantidade e qualidade mudam o preço. Por isso o app diz "acima da faixa de
  referência", nunca "superfaturado".
- A rede do ambiente de desenvolvimento bloqueia sites do governo; cada
  coletor é conferido com dados reais no GitHub Actions, como no federal.
