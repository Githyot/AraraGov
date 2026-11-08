# Processos e ocorrências

Seção do perfil que mostra se o político aparece em registros oficiais de
processos, sanções ou decisões da Justiça Eleitoral. O AraraGov **só informa**:
não dá nota, não faz ranking e não acusa ninguém.

## Fontes

| Fonte | O que entra | Como liga ao político |
|---|---|---|
| TSE, candidaturas de 2018 e 2022 (`consulta_cand`, `motivo_cassacao`) | Candidatura indeferida, cassada ou com recurso, e o motivo registrado; link da página da candidatura com as certidões criminais | Nome civil (ou de urna), cargo e estado. Nome repetido com CPFs diferentes fica de fora |
| CGU, CEIS e CNEP (Portal da Transparência) | Sanções a pessoas físicas, como a proibição de contratar com o poder público por improbidade (registrada pelo CNJ) | Nome igual **e** dígitos visíveis do CPF iguais aos do CPF da candidatura no TSE |
| TCU, inabilitados | Inabilitação para cargo em comissão ou função de confiança | Mesma regra da CGU |
| Lista curada (`araragov/referencia/processos.csv`) | Decisões de tribunais que não estão em cadastro aberto: prisão, condenação, absolvição, arquivamento | Feita à mão; só aceita link de site oficial (`.jus.br`, `.mp.br`, `.gov.br`, `.leg.br`, `.def.br`) |

Reportagens de imprensa **não** entram por enquanto: o risco de homônimo e de
difamação é alto, e a regra para elas ainda precisa ser aprovada.

## Cuidados

- **Presunção de inocência** (Constituição, art. 5º, LVII): a seção sempre lembra
  que processo em andamento não é condenação.
- **Situação atual** em todo item: em andamento, com recurso, condenação que cabe
  recurso, decisão definitiva, absolvido, arquivado, extinto, sanção em vigor ou
  encerrada.
- **Homônimos**: CGU e TCU só são cruzados quando o CPF confere. O CPF da
  candidatura é lido apenas em memória durante a coleta; não é gravado no banco
  nem publicado na API. Sem CPF conferível, o app diz "não conferido" naquela
  fonte, em vez de "nada encontrado".
- **Nada encontrado** não é atestado de "ficha limpa": o app diz quais fontes
  foram consultadas e que pode haver processos em outros tribunais.
- Nenhum selo ou contagem aparece na lista de políticos; a informação fica só
  dentro do perfil.
- Base legal (LGPD): dados tornados públicos por lei (Lei 9.504/1997, Lei
  12.846/2013, Lei 8.443/1992) e tratados para fins de transparência, com
  minimização (sem CPF publicado).

## Lista curada

Colunas (separadas por `;`): `casa;nome;tipo;titulo;situacao;data;orgao;processo;descricao;fonte`.
`situacao` precisa ser um destes valores: `em_andamento`, `recurso`, `condenado`,
`condenado_definitivo`, `absolvido`, `arquivado`, `extinto`, `sancao_vigente`,
`sancao_encerrada`, `decidido`, `informativo`. Linhas sem situação válida ou com
fonte não oficial são ignoradas. Quando a situação mudar (ex.: absolvição em
recurso), atualize a linha, não crie outra.

## Limites conhecidos

- O endereço JSON do TCU e o CPF nos arquivos do TSE são conferidos na primeira
  coleta real (a sondagem mostra a resposta). Se o TSE não publicar o CPF, CGU e
  TCU aparecem como "não conferido".
- Processos criminais no STF, STJ e tribunais estaduais não têm cadastro aberto
  único; por isso a lista curada.
