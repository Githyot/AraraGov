import 'package:araragov/dados/modelos.dart';
import 'package:araragov/telas/atuacao.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _perfil() => {
      'id': 'camara-1',
      'casa': 'camara',
      'cargo': 'Deputado Federal',
      'nome': 'Fulano',
      'salario_pago': {
        'total': 46366.19,
        'por_ano': [
          {'ano': 2026, 'valor': 46366.19}
        ],
        'anos': {
          '2026': {
            'total': 46366.19,
            'por_mes': [
              {'mes': 10, 'valor': 46366.19}
            ]
          }
        },
      },
      'quadro_recursos': {
        '2026': {'pessoal': 22, 'pessoal_ativo': 15, 'imovel': 'Não faz uso', 'auxilio': 'Não recebe o auxílio', 'viagens': 0, 'passaporte': 'Possui'},
      },
      'atividade': {
        'anos': {
          '2025': {
            'producao': {'propostas': [], 'relatorias': [], 'emendas': 1, 'requerimentos': 0, 'pedidos_informacao': 0},
          },
          '2026': {
            'producao': {
              'propostas': [
                [1, 'PL 10/2026', 'Cria o programa A.', '2026-03-01', null, 1],
                [2, 'PEC 3/2026', 'Altera a Constituição.', '2026-04-01', 'Aguardando Parecer', 0],
              ],
              'relatorias': [
                [77, 'PL 77/2015', 'Programa B.', '2026-06-03', 'pela aprovação', 'Pronta para Pauta'],
              ],
              'emendas': 4,
              'requerimentos': 9,
              'pedidos_informacao': 3,
            },
            'presenca': {'dias_presente': 74, 'dias_sessao': 77, 'periodo_parcial': false},
            'discursos': {
              'total': 2,
              'por_tipo': {'Pela ordem': 2},
              'recentes': [
                ['2026-11-04', 'Pela ordem', 'Sr. Presidente…', null]
              ],
            },
          },
        },
        'comissoes': {
          'itens': [
            ['CFT', 'Comissão de Finanças', 'Titular', '2025-03-18', null],
            ['CCJC', 'Comissão de Constituição e Justiça', 'Suplente', '2019-03-13', '2024-02-04'],
          ]
        },
        'frentes': {
          'legislatura': 57,
          'itens': [
            [3, 'Frente C', 1],
            [2, 'Frente A', 0],
          ]
        },
      },
    };

void main() {
  test('lê atuação parlamentar e quadro de recursos', () {
    final p = Perfil.fromJson(_perfil());
    final a = p.atividade!;
    expect(a.anoMostrado(null), 2026);
    expect(a.anoMostrado(2024), isNull);
    final prod = a.anos[2026]!.producao!;
    expect(prod.propostas.length, 2);
    expect(prod.comoPrimeiroAutor, 1);
    expect(prod.relatorias.single.link, 'https://www.camara.leg.br/propostas-legislativas/77');
    expect(a.anos[2026]!.presenca!.pct, closeTo(96.1, 0.1));
    expect(a.comissoes.where((c) => c.atual).single.sigla, 'CFT');
    expect(a.frentes.first.coordena, isTrue);
    expect(p.quadroRecursos[2026]!.pessoalAtivo, 15);
    expect(p.anosDisponiveis, containsAll([2025, 2026]));
    expect(p.noAno(2025).atividade!.anoMostrado(2025), 2025);
  });

  testWidgets('mostra recursos e atuação como a página da Câmara', (tester) async {
    final p = Perfil.fromJson(_perfil());
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ListView(children: [SecaoRecursos(p), SecaoAtuacao(p)])),
    ));
    expect(find.text('Recursos em 2026'), findsOneWidget);
    expect(find.text('22 pessoas em 2026, 15 no gabinete hoje'), findsOneWidget);
    expect(find.text('Não faz uso'), findsOneWidget);
    expect(find.text('Possui'), findsOneWidget);
    expect(find.text('Atuação parlamentar em 2026'), findsOneWidget);
    expect(find.text('1 como primeiro autor, 1 em coautoria'), findsOneWidget);
    expect(find.text('96,1%'), findsOneWidget);
    expect(find.text('1 hoje'), findsOneWidget);
  });

  test('perfil sem atuação (API antiga) não quebra', () {
    final p = Perfil.fromJson({'id': 'camara-1', 'casa': 'camara', 'cargo': 'Deputado Federal', 'nome': 'X'});
    expect(p.atividade, isNull);
    expect(p.quadroRecursos, isEmpty);
  });
}
