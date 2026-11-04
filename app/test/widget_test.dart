import 'dart:convert';

import 'package:araragov/dados/api.dart';
import 'package:araragov/formatar.dart';
import 'package:araragov/main.dart';
import 'package:flutter/material.dart';
import 'dart:io';

import 'package:araragov/telas/perfil.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _lista = '[{"id":"camara-1","casa":"camara","cargo":"Deputado Federal","nome":"Ana Exemplo",'
    '"partido":"PEX","uf":"SP","foto":null,"em_exercicio":true},'
    '{"id":"senado-2","casa":"senado","cargo":"Senador","nome":"Bruno Fictício",'
    '"partido":"PFI","uf":"BA","foto":null,"em_exercicio":true},'
    '{"id":"al-mg-3","casa":"al-mg","esfera":"estadual","orgao":"Assembleia Legislativa (MG)",'
    '"cargo":"Deputado estadual","nome":"Carla Inventada","partido":"PIN","uf":"MG","foto":null,"em_exercicio":true}]';

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

    await tester.tap(find.text('Estadual'));
    await tester.pumpAndSettle();
    expect(find.text('Ana Exemplo'), findsNothing);
    expect(find.text('Carla Inventada'), findsOneWidget);

    await tester.tap(find.text('Federal'));
    await tester.pumpAndSettle();
    expect(find.text('Carla Inventada'), findsNothing);
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

  testWidgets('perfil mostra posição, alinhamento e atenção', (tester) async {
    final json = File('assets/amostra/v1/politicos/camara-9001.json').readAsBytesSync();
    final client = MockClient((req) async => http.Response.bytes(json, 200));
    tester.view.physicalSize = const Size(800, 6000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(home: PerfilTela(api: Api(client: client), id: 'camara-9001')));
    await tester.pumpAndSettle();
    expect(find.text('Posição nas votações'), findsOneWidget);
    expect(find.text('Com quem vota junto'), findsOneWidget);
    expect(find.text('Votações que merecem atenção'), findsOneWidget);
    expect(find.textContaining('Votou com o lado da'), findsWidgets);
  });
}
