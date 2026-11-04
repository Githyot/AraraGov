# Roteiro do AraraGov

Linha de progresso do projeto: o que já está pronto, o que está em revisão e
o que falta. Este arquivo é atualizado a cada entrega.

Legenda: ✅ pronto (no `main`) · ✅ em revisão (PR aberto) · ⬜ falta fazer · ⏸️ só quando pedido

_Última atualização: 4 de novembro de 2026 (PRs #4, #5 e #6 no main)_

## Visão geral

| Etapa | Situação |
|---|---|
| 1. Base federal (Câmara, Senado, IPCA) | ✅ |
| 2. Análises (posição política, alinhamento, votações de atenção) | ✅ |
| 3. App multiplataforma (Flutter, visual GNOME) | ✅ primeira versão · ⏸️ builds só quando pedido |
| 4. Estados | ✅ início (TSE nos 27 estados, MG e SP) |
| Benefícios e custo dos gabinetes | ✅ Senado |
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
- ⬜ Câmara: salário dos assessores por nível (falta a tabela da Lei 15.349/2026)
- ⬜ Câmara: auxílio-moradia e imóvel funcional (a página da Câmara está atrás de login)
- ⬜ Outros penduricalhos: verba de gabinete total, passagens, plano de saúde
- ⬜ Fotos e dados de legislaturas anteriores
- ⬜ Emendas parlamentares (para onde vai o dinheiro de cada um)

## 2. Análises ✅

- ✅ Posição esquerda/direita pelos votos, em %, com faixa (esquerda, centro…)
- ✅ Cada votação classificada como de esquerda ou de direita
- ✅ Alinhamento com cada partido (mais e menos alinhados)
- ✅ Votações de atenção: aumento do próprio salário, fundo eleitoral, emendas,
  anistia, foro e imunidade, sem acusar ninguém
- ✅ Metodologia publicada e conferida com os dados reais de 2025
- ⬜ Comparar a posição pelos votos com o que o político declara (autodeclaração)
- ⬜ Mais votações do Senado (coletar 2019 em diante; o Senado vota pouco de forma nominal)

## 3. App ✅

- ✅ Flutter: um código para iOS, Android, Windows, Linux (e web)
- ✅ Visual no estilo GNOME, sem poluição visual
- ✅ Ícone: cabeça da Arara sobre a bandeira do Brasil
- ✅ Busca por nome, partido, estado e casa; perfil completo com gráficos
- ✅ Telas de posição política, alinhamento e votações de atenção
- ✅ Filtro Federal/Estadual e perfis estaduais
- ⬜ Filtro por período (ano/legislatura)
- ⬜ Comparar dois políticos lado a lado
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
