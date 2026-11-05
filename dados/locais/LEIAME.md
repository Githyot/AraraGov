# Dados da coleta local

Arquivos gravados por `python -m araragov coleta-local`, rodado uma vez por mês
num computador comum, porque a Caixa (SINAPI) e a Receita Federal (CNPJ)
recusam os servidores do GitHub. A coleta semanal lê estes arquivos.

- `sinapi/AAAA-MM.csv.gz`: custo de cada composição do SINAPI por estado (aba CSD,
  sem desoneração).
- `sinapi/candidatos-catalogo.csv`: composições que lembram cada item do catálogo
  de custos, para escolher os códigos em `araragov/referencia/custos_itens.csv`.
- `socios.csv.gz`: sócios das empresas que receberam de algum município, como a
  Receita publica (o CPF já vem mascarado pela Receita; não é publicado no app).
- `cnpjs-fornecedores.txt`: a lista de empresas usada para filtrar os sócios.

Passo a passo:

    python -m venv .venv && . .venv/bin/activate && pip install -e .
    python -m araragov coleta-local --mes 2025-09
    git add dados/locais && git commit -m "Coleta local de AAAA-MM" && git push
