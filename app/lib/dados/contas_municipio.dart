/// Contas de um município num ano, a partir do `{ano}.md` (Siconfi, DCA).
///
/// Junta as tabelas `receitas`, `destaques` e `areas` em totais e grupos que
/// a tela mostra: quanto entrou, de onde veio, quanto saiu e para onde foi.
library;

import 'md.dart';

double _n(String? v) => numeroMd(v) ?? 0;

/// Uma parcela com nome e valor (uma receita, uma área de gasto).
class Parcela {
  final String nome;
  final double valor;
  const Parcela(this.nome, this.valor);
}

/// Receitas agrupadas pela origem do dinheiro.
class GrupoReceita {
  final String nome;
  final double total;
  final List<Parcela> itens;
  const GrupoReceita(this.nome, this.total, this.itens);
}

/// Uma função de governo (saúde, educação…) com o que foi empenhado e pago.
class AreaGasto {
  final String funcao, nome;
  final double pago, empenhado;
  const AreaGasto(this.funcao, this.nome, this.pago, this.empenhado);
}

const nomeImpostos = 'Impostos e taxas da cidade';
const nomeRepasses = 'Repasses da União e do estado';
const nomeOutras = 'Outras receitas';

/// Abaixo desta fração do grupo, a sobra "Outros…" não vale uma linha.
const _sobraMinima = 0.005;

class ContasAno {
  final int ano;

  /// Leva reais de dezembro do ano até o último IPCA publicado.
  final double? fatorIpca;
  final String? ipcaAte;
  final int? populacao;

  /// Receita líquida (bruta menos deduções), soma das contas de nível 1.
  final double? arrecadado;
  final List<GrupoReceita> grupos;

  /// Soma das funções, fase paga e fase empenhada.
  final double? gasto, empenhado;
  final List<AreaGasto> areas;

  const ContasAno({
    required this.ano,
    this.fatorIpca,
    this.ipcaAte,
    this.populacao,
    this.arrecadado,
    this.grupos = const [],
    this.gasto,
    this.empenhado,
    this.areas = const [],
  });

  /// Positivo: arrecadou mais do que pagou no ano.
  double? get saldo => arrecadado == null || gasto == null ? null : arrecadado! - gasto!;

  /// Empenhado no ano e não pago até 31/12 (vira restos a pagar).
  double? get naoPago => empenhado == null || gasto == null ? null : empenhado! - gasto!;

  GrupoReceita? grupo(String nome) {
    for (final g in grupos) {
      if (g.nome == nome) return g;
    }
    return null;
  }

  /// Fração do arrecadado que veio de repasses de outros governos.
  double? get fracaoRepasses {
    final r = grupo(nomeRepasses);
    if (r == null || arrecadado == null || arrecadado! <= 0) return null;
    return r.total / arrecadado!;
  }

  double? porHabitante(double? valor) =>
      valor == null || populacao == null || populacao == 0 ? null : valor / populacao!;

  factory ContasAno.de(int ano, DocumentoMd doc) {
    final receitas = doc.tabela('receitas');
    int nivel(Map<String, String?> r) => int.tryParse(r['nivel'] ?? '') ?? 0;
    List<String> seg(String? codigo) => (codigo ?? '').split('.');

    // Origem pelo código da conta (Portaria Interministerial 163/2001):
    // 1.1 impostos e taxas; 1.7 e 2.4 transferências correntes e de capital.
    String origem(String? codigo) {
      final s = seg(codigo);
      if (s.length < 2) return nomeOutras;
      if (s[0] == '1' && s[1] == '1') return nomeImpostos;
      if ((s[0] == '1' && s[1] == '7') || (s[0] == '2' && s[1] == '4')) return nomeRepasses;
      return nomeOutras;
    }

    final nivel1 = receitas.where((r) => nivel(r) == 1).toList();
    final nivel2 = receitas.where((r) => nivel(r) == 2).toList();
    final arrecadado = nivel1.isEmpty ? null : nivel1.fold<double>(0, (s, r) => s + _n(r['liquida']));

    final totais = <String, double>{};
    for (final r in nivel2) {
      final o = origem(r['codigo']);
      totais[o] = (totais[o] ?? 0) + _n(r['liquida']);
    }
    final destaques = <String, List<Parcela>>{};
    for (final d in doc.tabela('destaques')) {
      final v = numeroMd(d['liquida']);
      if (v == null) continue;
      destaques.putIfAbsent(origem(d['codigo']), () => []).add(Parcela(d['destaque'] ?? '—', v));
    }

    final grupos = <GrupoReceita>[];
    for (final nome in [nomeImpostos, nomeRepasses]) {
      final itens = [...?destaques[nome]]..sort((a, b) => b.valor.compareTo(a.valor));
      final soma = itens.fold<double>(0, (s, p) => s + p.valor);
      // Sem as contas de nível 2, o grupo é só a soma dos destaques.
      final total = totais[nome] ?? soma;
      if (total == 0 && itens.isEmpty) continue;
      final sobra = total - soma;
      if (itens.isNotEmpty && sobra > total.abs() * _sobraMinima) {
        itens.add(Parcela(nome == nomeImpostos ? 'Outros impostos e taxas' : 'Outros repasses', sobra));
      }
      grupos.add(GrupoReceita(nome, total, itens));
    }
    final outras = [
      for (final r in nivel2)
        if (origem(r['codigo']) == nomeOutras && _n(r['liquida']) != 0) Parcela(r['conta'] ?? '—', _n(r['liquida'])),
    ]..sort((a, b) => b.valor.compareTo(a.valor));
    final totalOutras = totais[nomeOutras];
    if (totalOutras != null && totalOutras != 0) grupos.add(GrupoReceita(nomeOutras, totalOutras, outras));

    final funcoes = doc.tabela('areas').where((a) => a['subfuncao'] == null).toList();
    final areas = [
      for (final f in funcoes) AreaGasto(f['funcao'] ?? '', f['area'] ?? '—', _n(f['pago']), _n(f['empenhado'])),
    ]..sort((a, b) => b.pago.compareTo(a.pago));

    return ContasAno(
      ano: ano,
      fatorIpca: numeroMd(doc.meta['ipca_fator']),
      ipcaAte: doc.meta['ipca_ate'],
      populacao: int.tryParse(doc.meta['populacao'] ?? ''),
      arrecadado: arrecadado,
      grupos: grupos,
      gasto: funcoes.isEmpty ? null : areas.fold<double>(0, (s, a) => s + a.pago),
      empenhado: funcoes.isEmpty ? null : areas.fold<double>(0, (s, a) => s + a.empenhado),
      areas: areas,
    );
  }
}

/// Variação entre dois anos, em fração (0,05 = 5%), já descontada a inflação
/// quando os dois anos têm fator do IPCA; `real` diz qual foi o caso.
({double fracao, bool real})? variacao(ContasAno atual, ContasAno anterior, double? Function(ContasAno) valor) {
  final a = valor(atual), b = valor(anterior);
  if (a == null || b == null || b <= 0) return null;
  final fa = atual.fatorIpca, fb = anterior.fatorIpca;
  if (fa != null && fb != null) return (fracao: (a * fa) / (b * fb) - 1, real: true);
  return (fracao: a / b - 1, real: false);
}
