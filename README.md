# AraraGov

Dados públicos de políticos brasileiros, organizados e fáceis de entender.

Os portais oficiais publicam tudo o que a lei manda, mas espalhado, lento e
difícil de ler. O AraraGov coleta esses dados das fontes oficiais e mostra, para
cada político eleito: salário, gastos da cota parlamentar, gabinete, como votou
em cada votação, com quais partidos mais vota junto e se os gastos sobem mais
ou menos que a inflação.

O projeto é **apenas informativo**. Não acusa ninguém e não apoia extremismo de
nenhum lado. Toda informação tem link para a fonte oficial.

## Etapas

1. **Base de dados federal** (este repositório, em andamento): deputados,
   senadores, votações nominais, cota parlamentar, salários e IPCA.
2. **Análises**: alinhamento com partidos em %, posição geral no espectro
   político a partir das votações, votações que merecem atenção (ex.: aumento
   do próprio salário). Veja [docs/metodologia.md](docs/metodologia.md).
3. **App** multiplataforma (iOS, Android, Windows, Linux) em Flutter, seguindo
   as diretrizes de interface do GNOME.
4. **Estados e municípios**, começando pelos portais de transparência
   padronizados.

## Fontes

| Dado | Fonte |
|---|---|
| Deputados (nome, foto, partido, UF) | API Dados Abertos da Câmara |
| Votações e votos da Câmara | Arquivos anuais em massa da Câmara |
| Cota parlamentar da Câmara (CEAP) | `camara.leg.br/cotas/Ano-{ano}.csv.zip` |
| Senadores, votações do Senado | API Dados Abertos do Senado |
| Cota parlamentar do Senado (CEAPS) | API administrativa do Senado |
| Salário (subsídio) | Decretos legislativos, em [`araragov/referencia/subsidios.csv`](araragov/referencia/subsidios.csv) |
| Inflação (IPCA) | Banco Central, série SGS 433 |
| Processos e ocorrências | TSE (candidaturas), CGU (CEIS/CNEP), TCU (inabilitados) e lista curada de decisões em sites oficiais. Veja [docs/processos.md](docs/processos.md) |

## Como rodar

Requer Python 3.11+.

```bash
pip install -e '.[dev]'
pytest                                  # testes com respostas gravadas
araragov coletar tudo --ano 2025        # coleta completa (SQLite em ./dados)
araragov coletar camara-votacoes --ano 2025 --limite 20   # teste rápido
araragov resumo                         # quantos registros há no banco
```

Para usar Postgres: `pip install -e '.[postgres]'` e
`DATABASE_URL=postgresql+psycopg://usuario:senha@host/araragov`.

A coleta também roda no GitHub Actions (workflow **Coleta de dados**) toda
segunda-feira, e o banco gerado fica disponível para download na execução.

## Créditos

Parte do conhecimento sobre as fontes (formatos, limitações e armadilhas de
cada API) veio do [Mamute Político](https://github.com/correiosabia/mamute-politico-core),
do Correio Sabiá, também AGPL. Os dados de exemplo de cota parlamentar em
`tests/fixtures` vêm dos testes desse projeto.

A lista de municípios com o código do IBGE
(`araragov/referencia/municipios_ibge.csv`) vem do
[kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros), licença MIT.

## Licença

[AGPL-3.0](LICENSE). O código é aberto e qualquer serviço derivado também
precisa ser.
