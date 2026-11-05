# Roteiro do AraraGov

Linha de progresso do projeto: o que já está pronto, o que está em revisão e
o que falta. Este arquivo é atualizado a cada entrega.

Legenda: ✅ pronto (no `main`) · 🔄 em revisão (PR aberto) · ⬜ falta fazer · ➖ não disponível na fonte · ⏸️ só quando pedido

_Última atualização: 5 de novembro de 2026 (madrugada do dia 6)_

## Visão geral

| Etapa | Situação |
|---|---|
| 1. Base federal (Câmara, Senado, IPCA) | ✅ |
| 2. Análises (posição política, alinhamento, votações de atenção) | ✅ |
| 3. App multiplataforma (Flutter, visual GNOME) | ✅ primeira versão · ⏸️ builds só quando pedido |
| 4. Estados | ✅ início (TSE nos 27 estados, MG e SP) · 🔄 SC, BA e salário real por estado no PR #12 |
| Benefícios e custo dos gabinetes | ✅ Senado |
| Emendas parlamentares | ✅ |
| Período, comparação e doação do salário | ✅ |
| Base federal completa | ✅ |
| 5. Municípios | ⬜ aguardando as necessidades que HP vai trazer |

## 1. Base federal ✅

- ✅ Deputados federais e senadores: nome, foto, partido, UF, e-mail
- ✅ Todas as votações nominais e o voto de cada um (sim, não, abstenção, ausente…)
- ✅ Cota parlamentar (CEAP e CEAPS): gastos por mês, categoria e fornecedor
- ✅ Salário (subsídio) com o histórico e o ato legal de cada reajuste
- ✅ Inflação (IPCA): salário e gastos comparados com a inflação
- ✅ Gabinete: quem trabalha em cada gabinete (Câmara e Senado)
- ✅ API estática publicada no GitHub Pages, com coleta automática toda segunda-feira
- ✅ Coleta resiste a quedas das APIs do governo
- ✅ Senado: salário real de cada assessor (folha mensal) e custo mensal do gabinete
- ✅ Senado: auxílio-moradia e imóvel funcional de cada senador
- ✅ Câmara: verba de gabinete gasta por mês e custo mensal do gabinete
- ✅ Câmara: imóvel funcional, auxílio-moradia com o valor do ano, viagens em missão e passaporte diplomático
- ✅ Câmara: salário bruto pago a cada mês
- ➖ Câmara: salário de cada assessor. O robots.txt da Câmara pede para não coletar essas páginas; o custo total vem da verba de gabinete e o nível (SP01 a SP25) aparece na equipe
- ➖ Plano de saúde e reembolsos médicos: a Câmara e o Senado não publicam por parlamentar
- ✅ Histórico entre as coletas: os recursos da Câmara de anos fechados ficam guardados e só o que falta é buscado
- ✅ Doação do salário: mais declarações, com o período de cada uma
- ⬜ Seguir ampliando a lista de doações (cada nome com fonte pública)
- ✅ Legislatura anterior (2019-2022): deputados e senadores que saíram, votos e gastos desde 2019
- ✅ API mais leve: votos compactos nos perfis e detalhes das votações por ano, para caber no limite de 1 GB do GitHub Pages
- ✅ Emendas parlamentares: quanto cada um indicou, quanto foi pago, para onde e quem recebeu

## 2. Análises ✅

- ✅ Posição esquerda/direita pelos votos, em %, com faixa (esquerda, centro…)
- ✅ Cada votação classificada como de esquerda ou de direita
- ✅ Alinhamento com cada partido (mais e menos alinhados)
- ✅ Votações de atenção: aumento do próprio salário, fundo eleitoral, emendas,
  anistia, foro e imunidade, sem acusar ninguém
- ✅ Metodologia publicada e conferida com os dados reais de 2025
- ✅ Ideologia declarada pelo partido (PT, PCdoB, PDT, PL) ao lado da posição pelos votos, com a fonte
- ✅ Ideologia declarada também por PSB, PSOL e Republicanos
- ⬜ Declarações de políticos e dos partidos que faltam (cada uma com fonte)
- ✅ Votações do Senado desde 2019 (código pronto; conferir com dados reais quando a API do Senado voltar, hoje responde erro 503)

## 3. App ✅

- ✅ Flutter: um código para iOS, Android, Windows, Linux (e web)
- ✅ Visual no estilo GNOME, sem poluição visual
- ✅ Ícone: cabeça da Arara sobre a bandeira do Brasil
- ✅ Busca por nome, partido, estado e casa; perfil completo com gráficos
- ✅ Telas de posição política, alinhamento e votações de atenção
- ✅ Filtro Federal/Estadual e perfis estaduais
- ✅ Filtro por período (ano) no perfil
- ✅ Comparar dois políticos lado a lado, com % de votos iguais
- ✅ Doação do salário: quem declara doar, com a fonte, e filtro na busca
- ⏸️ Gerar os aplicativos (lojas e instaladores): só quando HP pedir

## 4. Estados (em andamento)

- ✅ Governadores, vices e deputados estaduais eleitos nos 27 estados (TSE)
- ✅ Minas Gerais (ALMG): deputados em exercício e verbas indenizatórias
- ✅ São Paulo (Alesp): deputados em exercício e despesas de gabinete
- ✅ Salário estadual mostrado como teto (75% do deputado federal)
- 🔄 Santa Catarina (Alesc): gastos de gabinete de cada deputado, de 2011 até hoje, do CSV aberto da Alesc (PR #12)
- 🔄 SC e BA: lista oficial de deputados em exercício; suplentes que assumiram ganham perfil e quem se afastou fica fora de exercício (PR #12)
- 🔄 Bahia (ALBA): verbas indenizatórias de cada deputado, da planilha anual da ALBA (sem o fornecedor, que a planilha não traz) (PR #12)
- 🔄 Salário real por estado, de uma lista com a fonte de cada valor (PR #12):
  - deputados estaduais de SC, SP e GO pela lei estadual; de PE pela imprensa (a lei não está acessível para conferir); do RJ pela página oficial da Alerj (valor atual); os outros estados seguem como teto até a lei ser conferida
  - governador e vice de SP pela lei estadual
  - governadores dos outros 26 estados pelo levantamento do Valor Econômico (out/2026), marcado no app como valor da imprensa
- 🔄 Seção sem dado mostra "Sem dados" e o órgão responsável por publicar, com a esfera (federal, estadual ou municipal); vale para todo o app (PR #12)
- ⬜ Conferir o salário de governador e deputados nos outros 22 estados
- ⬜ Outras assembleias, uma a uma, só com dados já publicados (sem pedidos ao governo):
  - ➖ PR: gastos só em telas e numa API que o robots.txt da Alep fecha; a API aberta só tem proposições
  - ➖ MT e MS: o site não publica os gastos de cada deputado (MT só traz as normas da verba; MS só explica a cota)
  - ⬜ PE, RS, ES, DF: portais não respondem fora do Brasil (tentado de novo em 05/11, sem sucesso)
  - ➖ RJ: os gastos dos deputados ficam no sistema DOCIGP, cujo robots.txt fecha todo o site (não coletamos)
- ⬜ Votações nominais estaduais (poucas assembleias publicam)
- ⬜ Gabinetes estaduais

## 5. Municípios ⬜

- ⬜ Levantar as necessidades com HP (foco em correção e desvio de dinheiro)
- ⬜ Portais padrão: Fiorilli, Betha, IPM
- ⬜ Prefeitos, vereadores, salários, gastos e contratos

## Pendências de configuração (HP)

- ⬜ Ativar o GitHub Pages com a fonte "GitHub Actions"
- ⬜ Rodar a "Coleta de dados" manualmente uma vez, para publicar a API
- ⬜ Apagar os ramos temporários `sondagem-gabinete`, `sondagem-federal` e `sondagem-assessores`
