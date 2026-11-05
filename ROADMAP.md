# Roteiro do AraraGov

Linha de progresso do projeto: o que já está pronto, o que está em revisão e
o que falta. Este arquivo é atualizado a cada entrega.

Legenda: ✅ pronto (no `main`) · 🔄 em revisão (PR aberto) · ⬜ falta fazer · ➖ não disponível na fonte · ⏸️ só quando pedido

_Última atualização: 5 de novembro de 2026 (noite)_

## Visão geral

| Etapa | Situação |
|---|---|
| 1. Base federal (Câmara, Senado, IPCA) | ✅ |
| 2. Análises (posição política, alinhamento, votações de atenção) | ✅ |
| 3. App multiplataforma (Flutter, visual GNOME) | ✅ primeira versão · ⏸️ builds só quando pedido |
| 4. Estados | ✅ início (TSE nos 27 estados, MG e SP) |
| Benefícios e custo dos gabinetes | ✅ Senado |
| Emendas parlamentares | ✅ |
| Período, comparação e doação do salário | ✅ |
| Base federal completa | ✅ · 🔄 histórico e listas curadas no PR #10 |
| 5. Municípios | 🔄 fases 0 a 4: plano, prefeitos e vereadores, finanças, custos de referência e o piloto de SP |

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
- 🔄 Histórico entre as coletas: os recursos da Câmara de anos fechados ficam guardados e só o que falta é buscado (PR #10)
- 🔄 Doação do salário: mais declarações, com o período de cada uma (PR #10)
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
- 🔄 Ideologia declarada também por PSB, PSOL e Republicanos (PR #10)
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
- ⬜ Salário real de cada assembleia e de cada governador (leis estaduais)
- ⬜ Outras assembleias com dados abertos (RJ, RS, PR, BA, PE…), uma a uma
- ⬜ Votações nominais estaduais (poucas assembleias publicam)
- ⬜ Gabinetes estaduais

## 5. Municípios (em andamento)

Plano completo em [docs/municipios.md](docs/municipios.md). Foco: arrecadação,
gastos por área, obras comparadas com o custo de referência e fornecedores,
sem acusar ninguém.

- ✅ Necessidades levantadas com HP
- 🔄 Fase 0: plano, formato `.md` que o app lê e metodologia de custo de referência em 3 níveis
- 🔄 Fase 1: prefeitos, vices e vereadores 2016/2020/2024 (TSE), um arquivo por município
- 🔄 Fase 2: arrecadação (IPTU, ISS, FPM…) e gastos por área e subárea, Brasil inteiro (Siconfi), com IPCA e aviso de quem não entregou
- 🔄 Fase 3: custo de referência em 3 níveis, com índice de custo por estado (SINAPI/IBGE) e períodos atípicos
- ⬜ Preço de cada serviço do SINAPI (o site da Caixa recusa downloads do GitHub) e preços de artigos com fonte
- 🔄 Fase 4: estado piloto (SP, pelo TCE-SP, porque o TCE-PR não responde ao GitHub): pagamentos por empresa e área, obras e contratos com comparação de custo
- ⬜ Fase 5: fornecedores, sócios (Receita), empresas punidas e indícios de vínculo com fonte
- ⬜ Fase 6: emendas e transferências até o CNPJ que recebeu
- ⬜ Fase 7: telas do app (município, área, obra, fornecedor)
- ⬜ Fase 8: outros TCEs e portais Fiorilli, Betha, IPM

## Pendências de configuração (HP)

- ⬜ Ativar o GitHub Pages com a fonte "GitHub Actions"
- ⬜ Rodar a "Coleta de dados" manualmente uma vez, para publicar a API
- ⬜ Apagar os ramos temporários `sondagem-gabinete` e `sondagem-federal`
