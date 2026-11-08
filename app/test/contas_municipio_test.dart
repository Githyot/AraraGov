import 'package:araragov/dados/contas_municipio.dart';
import 'package:araragov/dados/md.dart';
import 'package:flutter_test/flutter_test.dart';

// Valores inventados, só para o teste.
DocumentoMd _doc(String fator, double k) => lerMd('''---
formato: araragov-md/1
tipo: municipio-ano
populacao: 1000
ipca_fator: $fator
ipca_ate: 2026-09
---

<!-- tabela: destaques -->
| destaque | codigo | conta | liquida |
|---|---|---|---|
| IPTU | 1.1.1.2.50.0.0 | x | ${10 * k} |
| FPM | 1.7.1.8.01.2.0 | x | ${50 * k} |

<!-- tabela: receitas -->
| codigo | nivel | conta | bruta | deducoes | liquida |
|---|---|---|---|---|---|
| 1.0.0.0.00.0.0 | 1 | Receitas Correntes | ${100 * k} | 0 | ${100 * k} |
| 1.1.0.0.00.0.0 | 2 | Impostos | ${20 * k} | 0 | ${20 * k} |
| 1.3.0.0.00.0.0 | 2 | Receita Patrimonial | ${10 * k} | 0 | ${10 * k} |
| 1.7.0.0.00.0.0 | 2 | Transferências Correntes | ${70 * k} | 0 | ${70 * k} |

<!-- tabela: areas -->
| funcao | subfuncao | area | empenhado | liquidado | pago |
|---|---|---|---|---|---|
| 10 |  | Saúde | ${70 * k} | ${60 * k} | ${60 * k} |
| 10 | 301 | Atenção Básica | ${70 * k} | ${60 * k} | ${60 * k} |
| 12 |  | Educação | ${30 * k} | ${30 * k} | ${30 * k} |
''');

void main() {
  test('totais, grupos de receita e relações', () {
    final c = ContasAno.de(2025, _doc('1.0', 1));
    expect(c.arrecadado, 100);
    expect(c.gasto, 90);
    expect(c.empenhado, 100);
    expect(c.saldo, 10);
    expect(c.naoPago, 10);
    expect(c.porHabitante(c.gasto), 0.09);
    expect(c.fracaoRepasses, 0.7);
    expect([for (final g in c.grupos) g.nome], [nomeImpostos, nomeRepasses, nomeOutras]);
    final impostos = c.grupo(nomeImpostos)!;
    expect(impostos.total, 20);
    expect([for (final i in impostos.itens) (i.nome, i.valor)], [('IPTU', 10.0), ('Outros impostos e taxas', 10.0)]);
    expect(c.grupo(nomeOutras)!.itens.single.nome, 'Receita Patrimonial');
    expect([for (final a in c.areas) a.nome], ['Saúde', 'Educação']);
  });

  test('variação em relação ao ano anterior desconta a inflação', () {
    final atual = ContasAno.de(2025, _doc('1.0', 1.1));
    final anterior = ContasAno.de(2024, _doc('1.1', 1));
    final v = variacao(atual, anterior, (c) => c.gasto)!;
    expect(v.real, isTrue);
    expect(v.fracao, closeTo(0, 1e-9)); // subiu 10%, igual à inflação
  });
}
