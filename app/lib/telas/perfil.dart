import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import '../widgets/voto.dart';

class PerfilTela extends StatefulWidget {
  final Api api;
  final String id;
  final PoliticoResumo? resumo;
  final bool embutido;
  const PerfilTela({super.key, required this.api, required this.id, this.resumo, this.embutido = false});

  @override
  State<PerfilTela> createState() => _PerfilTelaState();
}

class _PerfilTelaState extends State<PerfilTela> {
  late Future<Perfil> _perfil = widget.api.perfil(widget.id);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !widget.embutido,
        title: Text(widget.resumo?.nome ?? ''),
      ),
      body: FutureBuilder<Perfil>(
        future: _perfil,
        builder: (context, snap) {
          if (snap.hasError) {
            return StatusPage(
              mascote: 'sad',
              titulo: 'Não foi possível carregar',
              descricao: '${snap.error}',
              acao: FilledButton(
                onPressed: () => setState(() => _perfil = widget.api.perfil(widget.id)),
                child: const Text('Tentar de novo'),
              ),
            );
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final p = snap.data!;
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: Adw.espaco, vertical: 24),
            children: [
              Clamp(
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  _Cabecalho(p),
                  const SizedBox(height: 24),
                  _SecaoSalario(p.salario),
                  _SecaoGastos(p.gastos),
                  _SecaoVotacoes(p),
                  _SecaoGabinete(p),
                  _Rodape(p),
                ]),
              ),
            ],
          );
        },
      ),
    );
  }
}

Future<void> _abrir(String? url) async {
  if (url != null) await launchUrl(Uri.parse(url));
}

class _Cabecalho extends StatelessWidget {
  final Perfil p;
  const _Cabecalho(this.p);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final r = p.resumo;
    return Column(children: [
      Avatar(url: r.foto, nome: r.nome, tamanho: 112),
      const SizedBox(height: 12),
      Text(r.nome, textAlign: TextAlign.center, style: tema.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
      if (p.nomeCivil != null && p.nomeCivil != r.nome)
        Text(p.nomeCivil!, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
      const SizedBox(height: 4),
      Text('${r.cargo} · ${r.partidoUf}', style: tema.textTheme.bodyLarge),
      if (!r.emExercicio) ...[
        const SizedBox(height: 8),
        const Etiqueta('Fora de exercício', Colors.grey),
      ],
    ]);
  }
}

/// Compara quanto um valor subiu com quanto a inflação subiu no mesmo período.
class _LinhaInflacao extends StatelessWidget {
  final String titulo;
  final ValorInflacao v;
  const _LinhaInflacao({required this.titulo, required this.v});

  @override
  Widget build(BuildContext context) {
    final subiu = v.valorInicial == 0 ? 0 : (v.valorAtual / v.valorInicial - 1) * 100;
    final inflacao = v.valorInicial == 0 ? 0 : (v.corrigido / v.valorInicial - 1) * 100;
    final acima = v.acimaPct;
    return Linha(
      titulo: titulo,
      subtitulo: 'Subiu ${porcentagem(subiu)}; a inflação foi ${porcentagem(inflacao)}. '
          'Só com a inflação seria ${reais(v.corrigido)}.',
      sufixo: Etiqueta(
        acima.abs() < 0.5 ? 'Igual à inflação' : '${porcentagem(acima, sinal: true)} vs inflação',
        // Cores neutras: destaca só quando subiu acima da inflação, sem julgar.
        acima > 0.5 ? Adw.amarelo : Colors.grey,
      ),
    );
  }
}

class _SecaoSalario extends StatelessWidget {
  final Salario s;
  const _SecaoSalario(this.s);

  @override
  Widget build(BuildContext context) {
    return Grupo(
      titulo: 'Salário',
      descricao: 'Subsídio bruto mensal, fixado por decreto legislativo',
      filhos: [
        Linha(titulo: 'Salário atual', valor: reais(s.atual)),
        if (s.vsInflacao != null)
          _LinhaInflacao(titulo: 'Desde ${mesAno(s.vsInflacao!.desde)}', v: s.vsInflacao!),
        if (s.historico.isNotEmpty)
          ExpansionTile(
            title: const Text('Histórico'),
            shape: const Border(),
            children: [
              for (final h in s.historico.reversed)
                Linha(titulo: 'Desde ${data(h.desde)}', subtitulo: h.ato, valor: reais(h.valor), aoTocar: h.fonte == null ? null : () => _abrir(h.fonte)),
            ],
          ),
      ],
    );
  }
}

class _SecaoGastos extends StatelessWidget {
  final Gastos g;
  const _SecaoGastos(this.g);

  @override
  Widget build(BuildContext context) {
    if (g.total == 0) {
      return const Grupo(titulo: 'Gastos da cota parlamentar', filhos: [Linha(titulo: 'Nenhum gasto registrado no período')]);
    }
    return Grupo(
      titulo: 'Gastos da cota parlamentar',
      descricao: 'Verba para despesas do mandato, como passagens, escritório e divulgação',
      filhos: [
        Linha(titulo: 'Total no período', valor: reais(g.total)),
        if (g.porAno.length > 1) Padding(padding: const EdgeInsets.fromLTRB(12, 16, 16, 8), child: _GraficoAnos(g.porAno)),
        for (final v in g.vsInflacao) _LinhaInflacao(titulo: 'Gasto em ${v.ano}', v: v),
        ExpansionTile(
          title: const Text('Por categoria'),
          shape: const Border(),
          children: [for (final c in g.porCategoria.take(8)) Linha(titulo: c.nome, valor: reaisCurto(c.valor))],
        ),
        ExpansionTile(
          title: const Text('Maiores fornecedores'),
          shape: const Border(),
          children: [for (final c in g.maioresFornecedores.take(8)) Linha(titulo: c.nome, valor: reaisCurto(c.valor))],
        ),
        ExpansionTile(
          title: const Text('Notas recentes'),
          shape: const Border(),
          children: [
            for (final d in g.documentos.take(10))
              Linha(
                titulo: d['fornecedor'] ?? 'Não informado',
                subtitulo: '${data(d['data'])} · ${d['categoria'] ?? ''}',
                valor: reais(d['valor']),
                aoTocar: d['url'] == null ? null : () => _abrir(d['url']),
              ),
          ],
        ),
      ],
    );
  }
}

class _GraficoAnos extends StatelessWidget {
  final List<({int ano, double valor})> anos;
  const _GraficoAnos(this.anos);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final maximo = anos.map((a) => a.valor).reduce((a, b) => a > b ? a : b);
    return SizedBox(
      height: 160,
      child: BarChart(BarChartData(
        maxY: maximo * 1.15,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (g, _, rod, _) => BarTooltipItem(reais(rod.toY), const TextStyle(color: Colors.white)),
          ),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(),
          rightTitles: const AxisTitles(),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 64,
              getTitlesWidget: (v, meta) => v == meta.max || v == 0
                  ? const SizedBox()
                  : Text(reaisCurto(v), style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (v, _) => Text('${anos[v.toInt()].ano}', style: tema.textTheme.bodySmall),
            ),
          ),
        ),
        barGroups: [
          for (var i = 0; i < anos.length; i++)
            BarChartGroupData(x: i, barRods: [
              BarChartRodData(
                toY: anos[i].valor,
                width: 28,
                color: tema.colorScheme.primary,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
              ),
            ]),
        ],
      )),
    );
  }
}

class _SecaoVotacoes extends StatelessWidget {
  final Perfil p;
  const _SecaoVotacoes(this.p);

  @override
  Widget build(BuildContext context) {
    if (p.votacoes.isEmpty) {
      return const Grupo(titulo: 'Votações', filhos: [Linha(titulo: 'Nenhuma votação nominal registrada')]);
    }
    final total = p.totalVotacoes;
    final pct = total == 0 ? 0 : p.participou / total * 100;
    final ordem = ['sim', 'nao', 'abstencao', 'obstrucao', 'ausente', 'licenca', 'missao', 'presidente', 'presente_sem_voto', 'outro'];
    return Grupo(
      titulo: 'Votações',
      descricao: 'Votações nominais em que o voto de cada parlamentar é registrado',
      acao: TextButton(
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TodasVotacoes(p))),
        child: const Text('Ver todas'),
      ),
      filhos: [
        Linha(titulo: 'Participação', subtitulo: 'Votou em ${p.participou} de $total votações', valor: porcentagem(pct)),
        Padding(
          padding: const EdgeInsets.all(12),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final k in ordem)
              if ((p.presenca[k] ?? 0) > 0) Etiqueta('${votoRotulo[k]}: ${p.presenca[k]}', votoCor(k)),
          ]),
        ),
        for (final v in p.votacoes.take(8)) LinhaVotacao(v),
      ],
    );
  }
}

class LinhaVotacao extends StatelessWidget {
  final VotoEmVotacao v;
  const LinhaVotacao(this.v, {super.key});

  @override
  Widget build(BuildContext context) => Linha(
        titulo: v.proposicao ?? v.descricao ?? 'Votação',
        subtitulo: [data(v.data), if (v.resultado != null) v.resultado!, if (v.ementa != null) v.ementa!].join(' · '),
        sufixo: EtiquetaVoto(v.voto),
        aoTocar: v.link == null ? null : () => _abrir(v.link),
      );
}

class TodasVotacoes extends StatelessWidget {
  final Perfil p;
  const TodasVotacoes(this.p, {super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Votações de ${p.resumo.nome}')),
        body: ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 12),
          itemCount: p.votacoes.length,
          separatorBuilder: (_, _) => const Clamp(child: Divider()),
          itemBuilder: (_, i) => Clamp(child: LinhaVotacao(p.votacoes[i])),
        ),
      );
}

class _SecaoGabinete extends StatelessWidget {
  final Perfil p;
  const _SecaoGabinete(this.p);

  @override
  Widget build(BuildContext context) {
    if (p.gabinete.isEmpty) return const SizedBox();
    return Grupo(
      titulo: 'Gabinete',
      descricao: '${p.gabinete.length} pessoas trabalham no gabinete',
      filhos: [
        ExpansionTile(
          title: const Text('Ver equipe'),
          shape: const Border(),
          children: [
            for (final a in p.gabinete)
              Linha(
                titulo: a.nome,
                subtitulo: [a.nivel ?? a.cargo, if (a.desde != null) 'desde ${data(a.desde)}'].whereType<String>().join(' · '),
              ),
          ],
        ),
      ],
    );
  }
}

class _Rodape extends StatelessWidget {
  final Perfil p;
  const _Rodape(this.p);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final fonte = p.resumo.casa == 'camara' ? 'Câmara dos Deputados' : 'Senado Federal';
    return Text(
      'Fonte: dados abertos do $fonte e Banco Central (IPCA). '
      'O AraraGov apenas organiza dados públicos e não faz acusações.',
      textAlign: TextAlign.center,
      style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
    );
  }
}
