import 'dart:convert';

import 'package:araragov/dados/api.dart';
import 'package:araragov/main.dart';
import 'package:araragov/tema.dart';
import 'package:araragov/widgets/adw.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _lista =
    '[{"id":"camara-1","casa":"camara","cargo":"Deputado Federal","nome":"Ana Exemplo",'
    '"partido":"PEX","uf":"SP","foto":null,"em_exercicio":true}]';

void main() {
  test('automático segue o sistema do aparelho', () {
    expect(EstiloVisual.automatico.resolver(TargetPlatform.linux), EstiloVisual.gnome);
    expect(EstiloVisual.automatico.resolver(TargetPlatform.android), EstiloVisual.android);
    expect(EstiloVisual.automatico.resolver(TargetPlatform.iOS), EstiloVisual.apple);
    expect(EstiloVisual.automatico.resolver(TargetPlatform.macOS), EstiloVisual.apple);
    expect(EstiloVisual.automatico.resolver(TargetPlatform.windows), EstiloVisual.windows);
    expect(EstiloVisual.windows.resolver(TargetPlatform.linux), EstiloVisual.windows);
  });

  test('todo estilo gera tema claro e escuro com os detalhes do sistema', () {
    for (final e in EstiloVisual.values.skip(1)) {
      for (final b in Brightness.values) {
        final t = temaPara(e, b);
        final v = t.extension<Visual>()!;
        expect(v.estilo, e);
        expect(t.brightness, b);
        expect(t.platform, e.plataforma);
      }
    }
    expect(temaPara(EstiloVisual.windows, Brightness.light).appBarTheme.centerTitle, isFalse);
    expect(temaPara(EstiloVisual.apple, Brightness.light).extension<Visual>()!.tituloGrupoMaiusculo, isTrue);
  });

  testWidgets('Grupo no estilo Apple põe o título em maiúsculas', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: temaPara(EstiloVisual.apple, Brightness.light),
        home: const Scaffold(
          body: Grupo(
            titulo: 'Gastos',
            filhos: [Linha(titulo: 'Cota')],
          ),
        ),
      ),
    );
    expect(find.text('GASTOS'), findsOneWidget);
  });

  testWidgets('troca o estilo em Aparência e o app muda na hora', (tester) async {
    final client = MockClient((req) async => http.Response.bytes(utf8.encode(_lista), 200));
    final aparencia = Aparencia(estilo: EstiloVisual.gnome, salvar: false);
    await tester.pumpWidget(
      AraraGovApp(
        api: Api(client: client),
        aparencia: aparencia,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Menu principal'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Aparência'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Windows'));
    await tester.pumpAndSettle();

    expect(aparencia.estilo, EstiloVisual.windows);
    final contexto = tester.element(find.text('Estilo atual: Windows'));
    expect(Theme.of(contexto).platform, TargetPlatform.windows);
  });
}
