import 'package:araragov/dados/modelos.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('lê processos e ocorrências com situação e fontes', () {
    final o = Ocorrencias.fromJson({
      'itens': [
        {'fonte': 'cgu', 'tipo': 'sancao', 'titulo': 'Impedimento (CEIS)', 'situacao': 'sancao_encerrada', 'data': '2020-01-01'},
        {'fonte': 'curado', 'tipo': 'acao_penal', 'titulo': 'Ação penal', 'situacao': 'absolvido'},
      ],
      'certidoes': [
        {'titulo': 'Certidões (2022)', 'link': 'https://divulgacandcontas.tse.jus.br/'}
      ],
      'fontes': [
        {'fonte': 'tse', 'nome': 'TSE', 'consultado_em': '2026-11-02', 'conferido': true},
        {'fonte': 'cgu', 'nome': 'CGU', 'consultado_em': '2026-11-01', 'conferido': false},
      ],
      'aviso': 'inocentes até a decisão final',
    });
    expect(o.itens.map((i) => i.situacaoRotulo), ['Sanção encerrada', 'Absolvido']);
    expect(o.certidoes.single.link, startsWith('https://'));
    expect(o.fontes.where((f) => f.conferido).length, 1);
  });

  test('perfil sem ocorrências (API antiga) não quebra', () {
    final p = Perfil.fromJson({'id': 'camara-1', 'casa': 'camara', 'cargo': 'Deputado Federal', 'nome': 'X'});
    expect(p.ocorrencias, isNull);
  });
}
