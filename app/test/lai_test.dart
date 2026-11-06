import 'package:araragov/widgets/lai.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('texto do pedido LAI cita a lei, o órgão e os itens, sem CPF', () {
    const p = PedidoLai(municipio: 'Recife', uf: 'PE', assunto: 'o contrato X', itens: ['Contrato', 'Notas fiscais']);
    expect(p.orgao, 'Prefeitura Municipal de Recife (PE)');
    expect(p.texto, contains('Lei 12.527/2011'));
    expect(p.texto, contains('1. Contrato'));
    expect(p.texto, contains('2. Notas fiscais'));
    expect(p.texto.toLowerCase(), isNot(contains('cpf')));
    expect(p.buscaEsic.toString(), contains('Recife'));
  });

  test('sem itens, pede empenho, contrato e notas', () {
    const p = PedidoLai(municipio: 'Juara', uf: 'MT', assunto: 'despesas');
    expect(p.texto, contains('Nota de empenho'));
    expect(p.texto, contains('3. '));
  });
}
