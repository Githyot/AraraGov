import 'dart:convert';

import 'package:araragov/dados/api.dart';
import 'package:araragov/formatar.dart';
import 'package:araragov/main.dart';
import 'package:flutter/material.dart';
import 'dart:io';

import 'package:araragov/dados/modelos.dart';
import 'package:araragov/telas/comparar.dart';
import 'package:araragov/telas/perfil.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _lista = '[{"id":"camara-1","casa":"camara","cargo":"Deputado Federal","nome":"Ana Exemplo",'
    '"partido":"PEX","uf":"SP","foto":null,"em_exercicio":true,"doa_salario":true},'
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
    await tester.pumpAndSettle();
    await tester.tap(find.text('Doa o salário'));
    await tester.pumpAndSettle();
    expect(find.text('Ana Exemplo'), findsOneWidget);
    expect(find.text('Bruno Fictício'), findsNothing);
    await tester.tap(find.text('Doa o salário'));
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
    expect(find.textContaining('se declara: Ideologia de exemplo'), findsOneWidget);
    expect(find.text('Com quem vota junto'), findsOneWidget);
    expect(find.text('Votações que merecem atenção'), findsOneWidget);
    // o rótulo é simétrico: aparece para os dois lados, e para quem não votou Sim/Não
    expect(find.text('Votou como a esquerda'), findsWidgets);
    expect(find.text('Votou como a direita'), findsWidgets);
    expect(find.text('Esquerda e direita votaram diferente'), findsWidgets);
    expect(find.text('Custo mensal com salários'), findsOneWidget);
    expect(find.text('Ocupa imóvel funcional em Brasília'), findsOneWidget);
    expect(find.text('Emendas parlamentares'), findsOneWidget);
  });

  test('filtra o perfil por ano e calcula votos em comum', () {
    Map<String, dynamic> ler(String id) =>
        jsonDecode(File('assets/amostra/v1/politicos/$id.json').readAsStringSync()) as Map<String, dynamic>;
    final a = Perfil.fromJson(ler('camara-9001'));
    final b = Perfil.fromJson(ler('camara-9002'));
    expect(a.anosDisponiveis, [2025, 2024, 2023]);
    expect(a.votacoes.length, 14); // compactos
    expect(a.votacoes.where((v) => v.temDetalhe).length, lessThan(14));
    final de2024 = a.noAno(2024);
    expect(de2024.votacoes, isEmpty);
    expect(de2024.gastos.total, a.gastos.porAno.firstWhere((x) => x.ano == 2024).valor);
    expect(de2024.emendas!.totalEmpenhado, 6500000);
    expect(a.noAno(null).votacoes.length, a.votacoes.length);
    final c = concordancia(a, b)!;
    expect(c.comuns, greaterThan(0));
    expect(c.iguais, lessThanOrEqualTo(c.comuns));
    expect(a.doacaoSalario!.titulo, 'Declara doar 20% do salário');
    expect(DoacaoSalario.fromJson({'parte': '30%', 'periodo': '2020', 'descricao': '', 'fonte': ''}).titulo,
        'Declarou doar 30% do salário em 2020');
  });

  test('salário estadual vindo da imprensa é marcado como referência', () {
    final s = Salario.fromJson({
      'atual': 21914.76,
      'observacao': 'Valor publicado pela imprensa',
      'historico': [
        {'desde': '2026-10-04', 'valor': 21914.76, 'ato': 'Levantamento', 'fonte': 'https://example.org', 'referencia': true}
      ],
    });
    expect(s.historico.single.referencia, isTrue);
    expect(s.teto, isFalse);
  });

  testWidgets('sem dados mostra o órgão responsável', (tester) async {
    final r = PoliticoResumo.fromJson({
      'id': 'al-mt-1', 'casa': 'al-mt', 'cargo': 'Deputado estadual', 'nome': 'X',
      'esfera': 'estadual', 'orgao': 'Assembleia Legislativa (MT)',
    });
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SemDados(r, detalhe: 'Equipe e custo do gabinete'))));
    expect(find.text('Sem dados'), findsOneWidget);
    expect(find.textContaining('Responsável por publicar: Assembleia Legislativa (MT) (esfera estadual)'), findsOneWidget);
    expect(executivo(PoliticoResumo.fromJson({'id': 'g', 'casa': 'gov-sp', 'cargo': 'Governador', 'nome': 'G'})), isTrue);
  });

  testWidgets('perfil troca o período e abre a comparação', (tester) async {
    final client = MockClient((req) async {
      final partes = req.url.pathSegments;
      final caminho = 'assets/amostra/v1/${partes.sublist(partes.indexOf('v1') + 1).join('/')}';
      return http.Response.bytes(File(caminho).readAsBytesSync(), 200);
    });
    tester.view.physicalSize = const Size(800, 6000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final api = Api(client: client);
    await tester.pumpWidget(MaterialApp(home: PerfilTela(api: api, id: 'camara-9001')));
    await tester.pumpAndSettle();
    expect(find.text('Declara doar 20% do salário'), findsOneWidget);
    expect(find.text('Salário bruto pago em 2025'), findsOneWidget);
    expect(find.text('Verba de gabinete gasta em 2025'), findsOneWidget);
    expect(find.text('Total recebido em 2025'), findsOneWidget);

    await tester.tap(find.text('Ver todas'));
    await tester.pumpAndSettle();
    expect(find.text('PL 111/2025'), findsOneWidget); // detalhe vindo de votacoes/2025.json
    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Período'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2024').last);
    await tester.pumpAndSettle();
    expect(find.text('Mostrando só 2024'), findsOneWidget);

    await tester.tap(find.byTooltip('Comparar com outro político'));
    await tester.pumpAndSettle();
    expect(find.text('Comparar com…'), findsOneWidget);
    await tester.tap(find.byType(ListTile).first);
    await tester.pumpAndSettle();
    expect(find.text('Lado a lado'), findsOneWidget);
    expect(find.text('Doação do salário'), findsOneWidget);
  });
}
