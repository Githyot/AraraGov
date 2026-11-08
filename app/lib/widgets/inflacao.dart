import 'package:flutter/material.dart';

import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import 'adw.dart';

/// Resultado de "subiu mais ou menos que a inflação?", com texto, cor e
/// ícone iguais em todas as telas (salário, cota, gabinete).
///
/// Tom neutro: amarelo chama atenção para o que subiu acima dos preços,
/// azul indica que subiu menos. Nenhuma das duas cores é "certo" ou "errado".
class Veredito {
  final String titulo;
  final Color cor;
  final IconData icone;
  const Veredito._(this.titulo, this.cor, this.icone);

  static const _margem = 0.5; // diferença em % considerada igual

  factory Veredito.de(double acimaPct) {
    if (acimaPct > _margem) return const Veredito._('Acima da inflação', Adw.amarelo, Icons.trending_up);
    if (acimaPct < -_margem) return const Veredito._('Abaixo da inflação', Adw.azul, Icons.trending_down);
    return const Veredito._('Igual à inflação', Colors.grey, Icons.trending_flat);
  }
}

/// Etiqueta com ícone: "↗ Acima da inflação".
class EtiquetaInflacao extends StatelessWidget {
  final double acimaPct;
  const EtiquetaInflacao(this.acimaPct, {super.key});

  @override
  Widget build(BuildContext context) {
    final v = Veredito.de(acimaPct);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(color: v.cor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(99)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(v.icone, size: 14, color: v.cor),
          const SizedBox(width: 4),
          Text(
            v.titulo,
            style: TextStyle(color: v.cor, fontWeight: FontWeight.bold, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

/// Uma barra horizontal com rótulo e valor, proporcional a [maximo].
class _Barra extends StatelessWidget {
  final String rotulo, valor;
  final double fracao;
  final Color cor;
  final bool tracejada;
  const _Barra({
    required this.rotulo,
    required this.valor,
    required this.fracao,
    required this.cor,
    this.tracejada = false,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(rotulo, style: tema.textTheme.bodyMedium)),
              Text(
                valor,
                style: tema.textTheme.bodyMedium?.copyWith(fontFeatures: const [FontFeature.tabularFigures()]),
              ),
            ],
          ),
          const SizedBox(height: 4),
          LayoutBuilder(
            builder: (context, c) => Align(
              alignment: Alignment.centerLeft,
              child: Container(
                height: 12,
                width: (c.maxWidth * fracao.clamp(0.02, 1.0)).toDouble(),
                decoration: BoxDecoration(
                  color: tracejada ? cor.withValues(alpha: 0.12) : cor,
                  border: tracejada ? Border.all(color: cor, width: 1.5) : null,
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Salário de hoje x o que seria se tivesse só acompanhado a inflação.
///
/// Mostra o veredito em uma frase e três barras: o valor no início, o valor
/// de hoje e o valor que teria só com a inflação.
class ComparacaoInflacao extends StatelessWidget {
  final ValorInflacao v;

  /// Ex.: "o salário". Usado nas frases.
  final String oQue;
  const ComparacaoInflacao(this.v, {super.key, this.oQue = 'o salário'});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final veredito = Veredito.de(v.acimaPct);
    final desde = mesAno(v.desde);
    final variacao = v.valorInicial == 0 ? 0.0 : (v.valorAtual / v.valorInicial - 1) * 100;
    final precos = v.valorInicial == 0 ? 0.0 : (v.corrigido / v.valorInicial - 1) * 100;
    final diferenca = (v.corrigido - v.valorAtual).abs();
    final maximo = [v.valorInicial, v.valorAtual, v.corrigido].reduce((a, b) => a > b ? a : b);
    final mudou = variacao >= 0 ? 'subiu ${porcentagem(variacao)}' : 'caiu ${porcentagem(variacao)}';

    final String frase;
    if (veredito.titulo == 'Igual à inflação') {
      frase = 'Desde $desde, $oQue $mudou e os preços subiram ${porcentagem(precos)}: acompanhou a inflação.';
    } else if (v.acimaPct > 0) {
      frase =
          'Desde $desde, $oQue $mudou e os preços subiram ${porcentagem(precos)}. '
          'Hoje é ${reais(diferenca)} (${porcentagem(v.acimaPct)}) maior do que seria só com a inflação.';
    } else {
      frase =
          'Desde $desde, $oQue $mudou e os preços subiram ${porcentagem(precos)}. '
          'Hoje é ${reais(diferenca)} (${porcentagem(v.acimaPct)}) menor do que seria só com a inflação.';
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 14, 16, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(veredito.icone, color: veredito.cor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  veredito.titulo,
                  style: tema.textTheme.titleMedium?.copyWith(color: veredito.cor, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(frase, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
          const SizedBox(height: 14),
          _Barra(
            rotulo: 'Em $desde',
            valor: reais(v.valorInicial),
            fracao: v.valorInicial / maximo,
            cor: tema.hintColor,
          ),
          _Barra(rotulo: 'Hoje', valor: reais(v.valorAtual), fracao: v.valorAtual / maximo, cor: veredito.cor),
          _Barra(
            rotulo: 'Se tivesse só acompanhado a inflação',
            valor: reais(v.corrigido),
            fracao: v.corrigido / maximo,
            cor: tema.hintColor,
            tracejada: true,
          ),
        ],
      ),
    );
  }
}

/// Gasto de um ano comparado com o gasto do ano-base corrigido pela inflação.
class LinhaInflacaoAno extends StatelessWidget {
  final ValorInflacao v;
  const LinhaInflacaoAno(this.v, {super.key});

  /// "2026 (jan–out, ano em andamento)" ou só "2026".
  static String tituloAno(ValorInflacao v) =>
      v.parcial ? '${v.ano} (${intervaloMeses(1, v.meses)}, ano em andamento)' : '${v.ano}';

  @override
  Widget build(BuildContext context) {
    final base = v.anoBase ?? (v.ano ?? 0) - 1;
    final referencia = v.parcial
        ? '${v.meses} meses do gasto de $base corrigido pela inflação (${reaisCurto(v.corrigido)})'
        : 'o gasto de $base corrigido pela inflação (${reaisCurto(v.corrigido)})';
    final String frase;
    if (Veredito.de(v.acimaPct).titulo == 'Igual à inflação') {
      frase = 'praticamente igual a $referencia';
    } else {
      frase = '${porcentagem(v.acimaPct)} ${v.acimaPct > 0 ? 'a mais' : 'a menos'} que $referencia';
    }
    return Linha(
      titulo: tituloAno(v),
      subtitulo: 'Gastou ${reaisCurto(v.valorAtual)}${v.parcial ? ' até agora' : ''}, $frase.',
      sufixo: EtiquetaInflacao(v.acimaPct),
    );
  }
}

/// Explica a base da comparação de gastos: qual ano e como ficam os meses.
String explicacaoBase(List<ValorInflacao> lista) {
  final v = lista.first;
  final base = v.anoBase ?? (v.ano ?? 0) - 1;
  final b = StringBuffer(
    'Cada ano é comparado com $base, o primeiro ano com gastos, corrigido pelo IPCA até o ano comparado.',
  );
  if (v.mesesBase < 12) b.write(' $base teve só ${v.mesesBase} meses de gastos, então a conta usa a média por mês.');
  if (lista.any((x) => x.parcial)) b.write(' O ano em andamento é comparado só com os mesmos meses.');
  return b.toString();
}
