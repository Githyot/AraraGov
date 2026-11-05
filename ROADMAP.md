# Roteiro do AraraGov

Linha de progresso do projeto: o que já está pronto, o que está em revisão e
o que falta. Este arquivo é atualizado a cada entrega.

Legenda: ✅ pronto (no `main`) · 🔄 em revisão (PR aberto) · ⬜ falta fazer · ➖ não disponível na fonte · ⏸️ só quando pedido

_Última atualização: 5 de novembro de 2026_

## Visão geral

| Etapa | Situação |
|---|---|
| 1. Base federal (Câmara, Senado, IPCA) | ✅ · 🔄 complemento no PR #9 |
| 2. Análises (posição política, alinhamento, votações de atenção) | ✅ |
| 3. App multiplataforma (Flutter, visual GNOME) | ✅ primeira versão · ⏸️ builds só quando pedido |
| 4. Estados | ✅ início (TSE nos 27 estados, MG e SP) |
| Benefícios e custo dos gabinetes | ✅ Senado |
| Emendas parlamentares | 🔄 PR #7 |
| Período, comparação e doação do salário | 🔄 PR #8 |
| Base federal completa | 🔄 PR #9 |
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
- 🔄 Câmara: verba de gabinete gasta por mês e custo mensal do gabinete (PR #9)
- 🔄 Câmara: imóvel funcional, auxílio-moradia com o valor do ano, viagens em missão e passaporte diplomático (PR #9)
- 🔄 Câmara: salário bruto pago a cada mês (PR #9)
- ➖ Câmara: salário de cada assessor. O robots.txt da Câmara pede para não coletar essas páginas; o custo total vem da verba de gabinete e o nível (SP01 a SP25) aparece na equipe
- ➖ Plano de saúde e reembolsos médicos: a Câmara e o Senado não publicam por parlamentar
- ⬜ Guardar o histórico entre as coletas (hoje os recursos da Câmara cobrem os 2 anos mais recentes)
- ⬜ Ampliar a lista de quem declara doar o salário (cada nome com fonte pública)
- 🔄 Legislatura anterior (2019-2022): deputados e senadores que saíram, votos e gastos desde 2019 (PR #9)
- 🔄 API mais leve: votos compactos nos perfis e detalhes das votações por ano, para caber no limite de 1 GB do GitHub Pages (PR #9)
- 🔄 Emendas parlamentares: quanto cada um indicou, quanto foi pago, para onde e quem recebeu (PR #7)

## 2. Análises ✅

- ✅ Posição esquerda/direita pelos votos, em %, com faixa (esquerda, centro…)
- ✅ Cada votação classificada como de esquerda ou de direita
- ✅ Alinhamento com cada partido (mais e menos alinhados)
- ✅ Votações de atenção: aumento do próprio salário, fundo eleitoral, emendas,
  anistia, foro e imunidade, sem acusar ninguém
- ✅ Metodologia publicada e conferida com os dados reais de 2025
- 🔄 Ideologia declarada pelo partido (PT, PCdoB, PDT, PL) ao lado da posição pelos votos, com a fonte (PR #9)
- ⬜ Ampliar as declarações: outros partidos e políticos que se declaram (cada um com fonte)
- 🔄 Votações do Senado desde 2019 (PR #9)

## 3. App ✅

- ✅ Flutter: um código para iOS, Android, Windows, Linux (e web)
- ✅ Visual no estilo GNOME, sem poluição visual
- ✅ Ícone: cabeça da Arara sobre a bandeira do Brasil
- ✅ Busca por nome, partido, estado e casa; perfil completo com gráficos
- ✅ Telas de posição política, alinhamento e votações de atenção
- ✅ Filtro Federal/Estadual e perfis estaduais
- 🔄 Filtro por período (ano) no perfil (PR #8)
- 🔄 Comparar dois políticos lado a lado, com % de votos iguais (PR #8)
- 🔄 Doação do salário: quem declara doar, com a fonte, e filtro na busca (PR #8)
- ⏸️ Gerar os aplicativos (lojas e instaladores): só quando HP pedir

## 4. Estados (em andamento)

- ✅ Governadores, vices e deputados estaduais eleitos nos 27 estados (TSE)
- ✅ Minas Gerais (ALMG): deputados em exercício e verbas indenizatórias
- ✅ São Paulo (Alesp): deputados em exercício e despesas de gabinete
- ✅ Salário estadual mostrado como teto (75% do deputado federal)
- ⬜ Salário real de cada assembleia e de cada governador (leis estaduais)
- ⬜ Outras assembleias com dados abertos (RJ, RS, PR, BA, PE…), uma a uma
- ⬜ Votações nominais estaduais (poucas assembleias publicam)
- ⬜ Gabinetes estaduais

## 5. Municípios ⬜

- ⬜ Levantar as necessidades com HP (foco em correção e desvio de dinheiro)
- ⬜ Portais padrão: Fiorilli, Betha, IPM
- ⬜ Prefeitos, vereadores, salários, gastos e contratos

## Pendências de configuração (HP)

- ⬜ Ativar o GitHub Pages com a fonte "GitHub Actions"
- ⬜ Rodar a "Coleta de dados" manualmente uma vez, para publicar a API
- ⬜ Apagar o ramo `sondagem-gabinete`
