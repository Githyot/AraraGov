# Formato `.md` dos dados

Os dados municipais e o banco de custos de referência são publicados em
Markdown com regras fixas. O mesmo arquivo serve para uma pessoa ler no
navegador (o GitHub mostra as tabelas formatadas) e para o app ler com um
leitor pequeno, sem bibliotecas extras.

Versão do formato: `araragov-md/1`.

## Exemplo

```markdown
---
formato: araragov-md/1
tipo: municipio-ano
ibge: 4104303
municipio: Campo Mourão
uf: PR
ano: 2024
atualizado: 2026-11-05
---

# Campo Mourão (PR), 2024

Texto livre para quem lê. O app ignora tudo o que não for cabeçalho ou tabela.

<!-- tabela: gastos-area -->
| area | subarea | valor_pago | fonte |
|---|---|---|---|
| Saúde | Atenção básica | 18234567.89 | https://siconfi.tesouro.gov.br |
| Urbanismo | Infraestrutura urbana | 9876543.21 | https://siconfi.tesouro.gov.br |
| Cultura |  | 120000 | https://siconfi.tesouro.gov.br |
```

## Regras

1. **Cabeçalho**: o arquivo começa com `---`, linhas `chave: valor` e outro
   `---`. Só uma chave por linha, sem listas nem níveis. `formato` e `tipo`
   são obrigatórios.
2. **Tabelas**: cada tabela vem logo depois de um comentário
   `<!-- tabela: id -->` (invisível no navegador). O `id` usa letras
   minúsculas, números e hífen, e não se repete no arquivo.
3. **Colunas**: a primeira linha da tabela tem os nomes das colunas (minúsculas,
   números e `_`); a segunda é a linha `|---|`.
4. **Números**: ponto como separador decimal e sem separador de milhar
   (`1234567.89`). O app formata para `R$ 1.234.567,89` na tela.
5. **Datas**: `AAAA-MM-DD` ou `AAAA-MM`.
6. **Vazio**: célula vazia quer dizer "sem dado", nunca zero.
7. **Barra vertical** dentro de uma célula é escrita como `\|`; quebras de
   linha viram espaço.
8. Linhas fora das tabelas e do cabeçalho são texto livre e o app as ignora.

## Por que Markdown

- Uma pessoa abre qualquer arquivo e confere os números com a fonte, sem
  ferramenta nenhuma. Isso faz parte da transparência do projeto.
- A tabela não repete o nome de cada campo em cada linha, como o JSON faz,
  então o arquivo fica menor.
- O app baixa só o arquivo que vai mostrar e guarda em cache.

## Leitores

- Python: `araragov/municipios/md.py` (`escrever` e `ler`), usado pela coleta.
- Dart: `app/lib/dados/md.dart` (`lerMd`), usado pelo app.

Os dois são testados com o mesmo exemplo.
