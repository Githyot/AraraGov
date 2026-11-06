import 'dart:convert';

import 'package:araragov/dados/api.dart';
import 'package:araragov/dados/tse.dart';
import 'package:araragov/telas/perfil_municipal.dart';
import 'package:araragov/telas/municipios.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

// Dados inventados, só para o teste.
const _indice = '''---
formato: araragov-md/1
tipo: municipios-indice
---

<!-- tabela: municipios -->
| ibge | tse | municipio | uf | prefeito | partido | mandato | vereadores |
|---|---|---|---|---|---|---|---|
| 3500105 | 61018 | Cidade Exemplo | SP | ANA TESTE | PEX | 2025-2028 | 1 |
| 1200013 | 1120 | Vila Fictícia | AC |  |  | 2025-2028 | 0 |
''';

const _resumo = '''---
formato: araragov-md/1
tipo: municipio-resumo
tse: 61018
---

<!-- tabela: mandatos -->
| eleicao | inicio | fim | cargo | nome | partido | sq_candidato |
|---|---|---|---|---|---|---|
| 2024 | 2025 | 2028 | Prefeito | ANA TESTE | PEX | 1 |
| 2024 | 2025 | 2028 | Vereador | BETO TESTE | PFI | 2 |
''';

const _contratos = '''---
formato: araragov-md/1
tipo: municipio-contratos
ano: 2024
---

<!-- tabela: obras -->
| contrato | cnpj | empresa | objeto | valor | unidade | valor_unitario | ref_minimo | ref_maximo | nivel | comparacao | aviso |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 11.222.333/0001-44 | OBRAS EXEMPLO LTDA | Recape da Rua A | 300000 | m² | 150 | 60 | 100 | 1 | 50.0% acima da faixa de referência |  |
''';

const _fornecedores = '''---
formato: araragov-md/1
tipo: municipio-fornecedores
---

<!-- tabela: fornecedores -->
| cnpj | empresa | pago | contratos | valor_contratos | indicios |
|---|---|---|---|---|---|
| 11.222.333/0001-44 | OBRAS EXEMPLO LTDA | 1000 | 1 | 300000 | Sanção no CEIS (Outra Prefeitura, 2023-2028) |

<!-- tabela: sem-dados -->
| secao | esfera | responsavel | motivo | obrigacao | fonte_consultada | consultado_em |
|---|---|---|---|---|---|---|
| socios | federal | Receita Federal | Sócios ainda não verificados. |  |  | 2026-11-05 |
''';

const _arquivos = {
  'municipios/indice.md': _indice,
  'municipios/sp/3500105/resumo.md': _resumo,
  'municipios/sp/3500105/2024-contratos.md': _contratos,
  'municipios/sp/3500105/fornecedores.md': _fornecedores,
};

Api _api() => Api(client: MockClient((req) async {
      final caminho = req.url.path.split('/v1/').last;
      final texto = _arquivos[caminho];
      return texto == null ? http.Response('', 404) : http.Response.bytes(utf8.encode(texto), 200);
    }));

void main() {
  testWidgets('busca municípios e mostra quem governa, obras e fornecedores', (tester) async {
    await tester.pumpWidget(MaterialApp(home: MunicipiosTela(api: _api())));
    await tester.pumpAndSettle();
    expect(find.text('Cidade Exemplo (SP)'), findsOneWidget);
    expect(find.text('Prefeito: não há dados'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'cidade');
    await tester.pumpAndSettle();
    expect(find.text('Vila Fictícia (AC)'), findsNothing);

    await tester.tap(find.text('Cidade Exemplo (SP)'));
    await tester.pumpAndSettle();
    expect(find.text('ANA TESTE'), findsOneWidget);

    // Cada pessoa abre um perfil, com foto do TSE (ou iniciais) e a ficha.
    await tester.tap(find.text('ANA TESTE'));
    await tester.pumpAndSettle();
    expect(find.text('Ficha no TSE'), findsOneWidget);
    expect(find.text('Mandatos em Cidade Exemplo'), findsOneWidget);
    expect(find.textContaining('ainda não foram coletados'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Obras'));
    await tester.pumpAndSettle();
    expect(find.text('Recape da Rua A'), findsOneWidget);
    expect(find.text('50,0% acima'), findsOneWidget);

    await tester.tap(find.text('Fornecedores'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Sanção no CEIS'), findsOneWidget);
    expect(find.text('Sócios ainda não verificados.'), findsOneWidget);

    await tester.tap(find.text('Emendas'));
    await tester.pumpAndSettle();
    expect(find.text('Não há dados'), findsOneWidget);
  });

  test('endereços do TSE e nome para ligar mandatos', () {
    expect(fotoTse('2024', '160002229427', '77577'),
        'https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2045202024/160002229427/77577');
    expect(paginaTse('2024', '160002229427', '77577'),
        'https://divulgacandcontas.tse.jus.br/divulga/#/candidato/2024/2045202024/77577/160002229427');
    expect(fotoTse('2024', null, '77577'), isNull);
    expect(fotoTse('2010', '1', '77577'), isNull);
    expect(chaveNome('Mário  Chotian'), chaveNome('MARIO CHOTIAN'));
  });
}
