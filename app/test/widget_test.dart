import 'dart:convert';

import 'package:araragov/dados/api.dart';
import 'package:araragov/formatar.dart';
import 'package:araragov/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _lista = '[{"id":"camara-1","casa":"camara","cargo":"Deputado Federal","nome":"Ana Exemplo",'
    '"partido":"PEX","uf":"SP","foto":null,"em_exercicio":true},'
    '{"id":"senado-2","casa":"senado","cargo":"Senador","nome":"Bruno Fictício",'
    '"partido":"PFI","uf":"BA","foto":null,"em_exercicio":true}]';

void main() {
  test('formata reais e porcentagem', () {
    expect(reais(46366.19), 'R\$ 46.366,19');
    expect(reais(-1234.5), '-R\$ 1.234,50');
    expect(reaisCurto(1250000), 'R\$ 1,3 mi');
    expect(porcentagem(-18.96, sinal: true), '−19,0%');
    expect(semAcento('Fictício'), 'Ficticio');
  });

  testWidgets('lista e filtra políticos', (tester) async {
    final client = MockClient((req) async => http.Response.bytes(utf8.encode(_lista), 200));
    await tester.pumpWidget(AraraGovApp(api: Api(client: client)));
    await tester.pumpAndSettle();
    expect(find.text('Ana Exemplo'), findsOneWidget);
    expect(find.text('Bruno Fictício'), findsOneWidget);

    await tester.tap(find.text('Senado'));
    await tester.pumpAndSettle();
    expect(find.text('Ana Exemplo'), findsNothing);
    expect(find.text('Bruno Fictício'), findsOneWidget);

    await tester.tap(find.text('Todos'));
    await tester.enterText(find.byType(TextField), 'ficticio');
    await tester.pumpAndSettle();
    expect(find.text('Bruno Fictício'), findsOneWidget);
    expect(find.text('Ana Exemplo'), findsNothing);
  });

  testWidgets('mostra erro com a Arara quando a API falha', (tester) async {
    final client = MockClient((req) async => http.Response('erro', 500));
    await tester.pumpWidget(AraraGovApp(api: Api(client: client)));
    await tester.pumpAndSettle();
    expect(find.text('Não foi possível carregar'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Tentar de novo'), findsOneWidget);
  });
}
