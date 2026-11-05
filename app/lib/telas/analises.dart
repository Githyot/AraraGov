import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/modelos.dart';
import '../formatar.dart';
import '../widgets/adw.dart';

const _rotuloFaixa = {
  'esquerda': 'Esquerda',
  'centro-esquerda': 'Centro-esquerda',
  'centro': 'Centro',
  'centro-direita': 'Centro-direita',
  'direita': 'Direita',
};

String rotuloFaixa(String? f) => _rotuloFaixa[f] ?? '—';

/// Barra horizontal esquerda x direita, com cores neutras.
class BarraEspectro extends StatelessWidget {
  final double pctEsquerda;
  final double? marcador; // média do partido, em % à esquerda
  const BarraEspectro({super.key, required this.pctEsquerda, this.marcador});

  @override
  Widget build(BuildContext context) {
    final cor = Theme.of(context).colorScheme;
    final tema = Theme.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      LayoutBuilder(builder: (context, c) {
        final w = c.maxWidth;
        return SizedBox(
          height: 18,
          child: Stack(clipBehavior: Clip.none, children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(9),
              child: Row(children: [
                Expanded(flex: (pctEsquerda * 10).round().clamp(1, 1000), child: Container(color: cor.primary)),
                Expanded(flex: ((100 - pctEsquerda) * 10).round().clamp(1, 1000), child: Container(color: cor.outlineVariant)),
              ]),
            ),
            if (marcador != null)
              Positioned(
                // o marcador mostra onde fica a média do partido
                left: (w * marcador! / 100).clamp(0, w) - 1.5,
                top: -4,
                child: Container(width: 3, height: 26, color: cor.onSurface),
              ),
          ]),
        );
      }),
      const SizedBox(height: 6),
      Row(children: [
        Text('Esquerda ${porcentagem(pctEsquerda)}', style: tema.textTheme.bodySmall),
        const Spacer(),
        Text('Direita ${porcentagem(100 - pctEsquerda)}', style: tema.textTheme.bodySmall),
      ]),
    ]);
  }
}

class SecaoPosicao extends StatelessWidget {
  final Perfil p;
  const SecaoPosicao(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final pos = p.posicao;
    if (pos == null) return const SizedBox();
    final partido = p.resumo.partido;
    return Grupo(
      titulo: 'Posição nas votações',
      descricao: 'Calculada pelos votos; abaixo, o que a pessoa ou o partido declaram',
      filhos: [
        Linha(titulo: 'Na prática, vota mais com', valor: rotuloFaixa(pos.faixa)),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
          child: BarraEspectro(pctEsquerda: pos.pctEsquerda, marcador: pos.mediaPartido),
        ),
        if (pos.mediaPartido != null && partido != null)
          Linha(
            titulo: 'Média do $partido',
            subtitulo: 'A linha escura na barra marca a média do partido',
            valor: rotuloFaixa(pos.faixaPartido),
          ),
        if (p.ideologiaPessoal != null) _LinhaDeclaracao('Declara-se', p.ideologiaPessoal!),
        if (p.ideologiaPartido != null && partido != null) _LinhaDeclaracao('O $partido se declara', p.ideologiaPartido!),
        ExpansionTile(
          title: const Text('Como calculamos'),
          shape: const Border(),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Text(
              'Usamos ${pos.votacoes} votações em que a esquerda (PT, PSOL e PCdoB) e a direita '
              '(PL e NOVO) votaram em lados opostos. O percentual mostra em quantas delas esta pessoa '
              'votou como cada lado. Votações em que os dois lados concordam ficam de fora. '
              'É um retrato dos votos, não um julgamento.',
            ),
          ],
        ),
      ],
    );
  }
}

/// O que o partido ou a pessoa diz sobre a própria ideologia, com a fonte.
class _LinhaDeclaracao extends StatelessWidget {
  final String titulo;
  final Declaracao d;
  const _LinhaDeclaracao(this.titulo, this.d);

  @override
  Widget build(BuildContext context) {
    final partes = [
      if (d.trecho != null) '“${d.trecho}”',
      if (d.documento != null) d.documento!,
    ];
    return Linha(
      titulo: '$titulo: ${d.declaracao}',
      subtitulo: partes.isEmpty ? null : partes.join('\n'),
      aoTocar: d.fonte == null ? null : () => launchUrl(Uri.parse(d.fonte!)),
    );
  }
}

class SecaoAlinhamento extends StatelessWidget {
  final Perfil p;
  const SecaoAlinhamento(this.p, {super.key});

  Widget _linha(BuildContext context, AlinhamentoPartido a) {
    final cor = Theme.of(context).colorScheme;
    return ListTile(
      title: Row(children: [
        SizedBox(width: 110, child: Text(a.partido)),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: a.pct / 100,
              minHeight: 8,
              color: cor.primary,
              backgroundColor: cor.outlineVariant,
            ),
          ),
        ),
        SizedBox(width: 64, child: Text(porcentagem(a.pct), textAlign: TextAlign.end)),
      ]),
      subtitle: Text('${a.votacoes} votações em comum'),
    );
  }

  @override
  Widget build(BuildContext context) {
    final al = p.alinhamento;
    if (al == null || al.maisAlinhados.isEmpty) return const SizedBox();
    return Grupo(
      titulo: 'Com quem vota junto',
      descricao: '% das votações em que votou igual à maioria de cada partido',
      filhos: [
        if (al.proprioPartido != null)
          Linha(titulo: 'Com o próprio partido (${al.proprioPartido!.partido})', valor: porcentagem(al.proprioPartido!.pct)),
        for (final a in al.maisAlinhados) _linha(context, a),
        if (al.menosAlinhados.isNotEmpty)
          ExpansionTile(
            title: const Text('Partidos com quem menos vota junto'),
            shape: const Border(),
            children: [for (final a in al.menosAlinhados) _linha(context, a)],
          ),
      ],
    );
  }
}

class SecaoAtencao extends StatelessWidget {
  final Perfil p;
  final VoidCallback aoVer;
  const SecaoAtencao(this.p, {super.key, required this.aoVer});

  @override
  Widget build(BuildContext context) {
    final a = p.atencao;
    if (a == null) return const SizedBox();
    return Grupo(
      titulo: 'Votações que merecem atenção',
      descricao: 'Temas que afetam os próprios parlamentares, como salário, fundo eleitoral e emendas. '
          'Não é acusação: é um convite para olhar com calma.',
      filhos: [
        Linha(titulo: 'Votações desse tipo', valor: '${a.votacoes}'),
        Linha(titulo: 'Votou Sim', valor: '${a.votouSim}'),
        Linha(titulo: 'Votou Não', valor: '${a.votouNao}'),
        Linha(titulo: 'Ver essas votações', aoTocar: aoVer),
      ],
    );
  }
}
