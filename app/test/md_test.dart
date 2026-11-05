import 'dart:io';

import 'package:araragov/dados/md.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('lê o exemplo compartilhado com o leitor Python', () {
    final texto = File('../tests/fixtures/formato-md-exemplo.md').readAsStringSync();
    final doc = lerMd(texto);
    expect(doc.meta['tipo'], 'municipio-ano');
    expect(doc.meta['municipio'], 'Campo Mourão');
    final gastos = doc.tabela('gastos-area');
    expect(gastos, hasLength(3));
    expect(numeroMd(gastos[0]['valor_pago']), 18234567.89);
    expect(gastos[2]['subarea'], isNull);
    expect(doc.tabela('pagamentos').single['favorecido'], 'Empresa | Exemplo Ltda');
    expect(doc.colunas['pagamentos'], ['cnpj', 'favorecido', 'valor', 'data']);
    expect(doc.tabela('nao-existe'), isEmpty);
  });

  test('rejeita arquivos fora do formato', () {
    for (final texto in [
      'sem cabeçalho',
      '---\nformato: outro/1\ntipo: t\n---\n',
      '---\nformato: araragov-md/1\n---\n',
      '---\nformato: araragov-md/1\ntipo: t\n---\n<!-- tabela: a -->\n| x | y |\n|---|---|\n| 1 |\n',
      '---\nformato: araragov-md/1\ntipo: t\n---\n<!-- tabela: a -->\n| x |\n| 1 |\n',
    ]) {
      expect(() => lerMd(texto), throwsA(isA<ErroFormatoMd>()), reason: texto);
    }
  });
}
