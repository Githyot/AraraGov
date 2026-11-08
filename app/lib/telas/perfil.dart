import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import '../widgets/inflacao.dart';
import '../widgets/voto.dart';
import 'analises.dart';
import 'comparar.dart';

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
  int? _ano;

  @override
  void didUpdateWidget(PerfilTela antigo) {
    super.didUpdateWidget(antigo);
    if (antigo.id != widget.id) {
      _perfil = widget.api.perfil(widget.id);
      _ano = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !widget.embutido,
        title: Text(widget.resumo?.nome ?? ''),
        actions: [
          FutureBuilder<Perfil>(
            future: _perfil,
            builder: (context, snap) {
              if (!snap.hasData) return const SizedBox();
              final anos = snap.data!.anosDisponiveis;
              return Row(mainAxisSize: MainAxisSize.min, children: [
                if (anos.length > 1)
                  PopupMenuButton<int>(
                    tooltip: 'Período',
                    icon: const Icon(Icons.calendar_month_outlined),
                    initialValue: _ano ?? 0,
                    onSelected: (v) => setState(() => _ano = v == 0 ? null : v),
                    itemBuilder: (_) => [
                      const PopupMenuItem(value: 0, child: Text('Todo o período')),
                      for (final a in anos) PopupMenuItem(value: a, child: Text('$a')),
                    ],
                  ),
                IconButton(
                  tooltip: 'Comparar com outro político',
                  icon: const Icon(Icons.compare_arrows),
                  onPressed: () => abrirComparacao(context, widget.api, snap.data!.noAno(_ano)),
                ),
              ]);
            },
          ),
        ],
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
          final p = snap.data!.noAno(_ano);
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: Adw.espaco, vertical: 24),
            children: [
              Clamp(
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  _Cabecalho(p),
                  if (_ano != null) ...[
                    const SizedBox(height: 12),
                    Center(
                      child: InputChip(
                        label: Text('Mostrando só $_ano'),
                        onDeleted: () => setState(() => _ano = null),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Votos, posição, alinhamento, cota, verba e emendas são só de $_ano. '
                      'Tabela de salário e equipe do gabinete são as atuais.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
                    ),
                  ],
                  const SizedBox(height: 24),
                  SecaoPosicao(p),
                  SecaoAlinhamento(p),
                  _SecaoSalario(p.salario, r: p.resumo, beneficios: p.beneficios, doacao: p.doacaoSalario, pago: p.salarioPago),
                  _SecaoGastos(p.gastos, r: p.resumo, estadual: p.resumo.esfera == 'estadual'),
                  if (p.emendas != null) _SecaoEmendas(p.emendas!),
                  if (!executivo(p.resumo)) _SecaoVotacoes(p, widget.api),
                  SecaoAtencao(
                    p,
                    aoVer: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => TodasVotacoes(p, api: widget.api, soAtencao: true)),
                    ),
                  ),
                  _SecaoOcorrencias(p),
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
      if (r.orgao.isNotEmpty) Text(r.orgao, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
      if (p.avisoCadastro != null) ...[
        const SizedBox(height: 8),
        Text(p.avisoCadastro!, textAlign: TextAlign.center, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
      ],
      if (!r.emExercicio) ...[
        const SizedBox(height: 8),
        const Etiqueta('Fora de exercício', Colors.grey),
      ],
    ]);
  }
}

class _SecaoSalario extends StatelessWidget {
  final Salario s;
  final List<Beneficio> beneficios;
  final DoacaoSalario? doacao;
  final ValoresMensais? pago;
  const _SecaoSalario(this.s, {required this.r, this.beneficios = const [], this.doacao, this.pago});
  final PoliticoResumo r;

  Widget? _linhaPago() {
    final ano = pago?.ultimoAno;
    if (ano == null) return null;
    final doAno = pago!.anos[ano]!;
    return ExpansionTile(
      title: Text('Salário bruto pago em $ano'),
      subtitle: Text('${reais(doAno.total)} em ${doAno.porMes.length} meses'),
      shape: const Border(),
      children: [for (final m in doAno.porMes) Linha(titulo: _nomeMes(m.mes), valor: reais(m.valor))],
    );
  }

  Widget _linhaDoacao(DoacaoSalario d) => Linha(
        prefixo: const Icon(Icons.volunteer_activism_outlined),
        titulo: d.titulo,
        subtitulo: '${d.descricao}\nDeclaração pública do próprio político; o AraraGov não confere a doação.',
        aoTocar: () => _abrir(d.fonte),
      );

  @override
  Widget build(BuildContext context) {
    if (s.atual == null) {
      return Grupo(titulo: 'Salário', filhos: [
        SemDados(r, detalhe: s.observacao),
        if (doacao != null) _linhaDoacao(doacao!),
        ?_linhaPago(),
        for (final b in beneficios) Linha(titulo: b.descricao, subtitulo: 'Benefício além do salário'),
      ]);
    }
    return Grupo(
      titulo: 'Salário',
      descricao: s.observacao ?? 'Subsídio bruto mensal, fixado por decreto legislativo',
      filhos: [
        Linha(
          titulo: s.teto ? 'Teto do salário' : 'Salário atual',
          subtitulo: s.historico.isEmpty ? null : s.historico.last.ato,
          valor: reais(s.atual),
          aoTocar: s.historico.isEmpty || s.historico.last.fonte == null ? null : () => _abrir(s.historico.last.fonte),
        ),
        if (s.vsInflacao != null) ComparacaoInflacao(s.vsInflacao!, oQue: s.teto ? 'o teto do salário' : 'o salário'),
        if (doacao != null) _linhaDoacao(doacao!),
        ?_linhaPago(),
        for (final b in beneficios)
          Linha(
            titulo: b.descricao,
            subtitulo: b.valorAno != null && b.ano != null
                ? 'Total recebido em ${b.ano}'
                : b.referencia == null
                    ? 'Benefício além do salário'
                    : 'Benefício além do salário · ${b.referencia}',
            valor: b.valorMensal != null
                ? reais(b.valorMensal)
                : b.valorAno != null
                    ? reais(b.valorAno, centavos: false)
                    : null,
            aoTocar: b.fonte == null ? null : () => _abrir(b.fonte),
          ),
        if (s.historico.isNotEmpty)
          ExpansionTile(
            title: const Text('Histórico'),
            shape: const Border(),
            children: [
              for (final h in s.historico.reversed)
                Linha(titulo: h.referencia ? 'Valor em ${mesAno(h.desde)}' : 'Desde ${data(h.desde)}', subtitulo: h.ato, valor: reais(h.valor), aoTocar: h.fonte == null ? null : () => _abrir(h.fonte)),
            ],
          ),
      ],
    );
  }
}

class _SecaoGastos extends StatelessWidget {
  final Gastos g;
  final bool estadual;
  final PoliticoResumo r;
  const _SecaoGastos(this.g, {required this.r, this.estadual = false});

  @override
  Widget build(BuildContext context) {
    final titulo = rotuloGastos(r);
    if (g.total == 0) {
      return Grupo(titulo: titulo, filhos: [SemDados(r)]);
    }
    return Grupo(
      titulo: titulo,
      descricao: estadual
          ? 'Verba indenizatória do mandato, como combustível, escritório e divulgação'
          : 'Verba para despesas do mandato, como passagens, escritório e divulgação',
      filhos: [
        Linha(titulo: 'Total no período', valor: reais(g.total)),
        if (g.porAno.length > 1)
          Padding(padding: const EdgeInsets.fromLTRB(12, 16, 16, 8), child: _GraficoAnos(g.porAno, inflacao: g.vsInflacao)),
        if (g.vsInflacao.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 16, 8),
            child: Text(explicacaoBase(g.vsInflacao),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor)),
          ),
          for (final v in g.vsInflacao) LinhaInflacaoAno(v),
        ],
        _PorCategoria(g),
        ExpansionTile(
          title: const Text('Maiores fornecedores'),
          shape: const Border(),
          children: [for (final c in g.maioresFornecedores.take(8)) Linha(titulo: nomeLegivel(c.nome), valor: reaisCurto(c.valor))],
        ),
        ExpansionTile(
          title: const Text('Notas recentes'),
          shape: const Border(),
          children: [
            for (final d in g.documentos.take(10))
              Linha(
                titulo: nomeLegivel(d['fornecedor'] ?? 'Não informado'),
                subtitulo: '${data(d['data'])} · ${nomeLegivel(d['categoria'] ?? '')}',
                valor: reais(d['valor']),
                aoTocar: d['url'] == null ? null : () => _abrir(d['url']),
              ),
          ],
        ),
      ],
    );
  }
}

class _SecaoEmendas extends StatelessWidget {
  final Emendas e;
  const _SecaoEmendas(this.e);

  @override
  Widget build(BuildContext context) {
    return Grupo(
      titulo: 'Emendas parlamentares',
      descricao: 'Dinheiro do orçamento federal que o parlamentar indicou para áreas e lugares',
      filhos: [
        Linha(titulo: 'Indicado (empenhado)', subtitulo: '${e.quantidade} emendas', valor: reais(e.totalEmpenhado)),
        Linha(titulo: 'Já pago', valor: reais(e.totalPago)),
        if (e.porAno.length > 1) Padding(padding: const EdgeInsets.fromLTRB(12, 16, 16, 8), child: _GraficoAnos(e.porAno)),
        ExpansionTile(
          title: const Text('Por área'),
          shape: const Border(),
          children: [for (final a in e.porArea) Linha(titulo: nomeLegivel(a.nome), valor: reaisCurto(a.valor))],
        ),
        ExpansionTile(
          title: const Text('Para onde foi'),
          shape: const Border(),
          children: [for (final a in e.porLocal) Linha(titulo: nomeLegivel(a.nome), valor: reaisCurto(a.valor))],
        ),
        if (e.favorecidos.isNotEmpty)
          ExpansionTile(
            title: const Text('Quem recebeu'),
            shape: const Border(),
            children: [
              for (final f in e.favorecidos)
                Linha(
                  titulo: f.nome,
                  subtitulo: [f.municipio, f.uf].whereType<String>().join(' · '),
                  valor: reaisCurto(f.valor),
                ),
            ],
          ),
      ],
    );
  }
}

class _GraficoAnos extends StatelessWidget {
  /// Se vier, cada ano ganha uma segunda barra contornada: o gasto do ano-base
  /// corrigido pela inflação. A barra do gasto fica amarela quando passa dela.
  final List<ValorInflacao> inflacao;

  /// Mostra no eixo os anos do meio que não têm dados, sem barra, e avisa abaixo.
  final bool marcarAnosSemDados;
  const _GraficoAnos(List<({int ano, double valor})> anos, {this.inflacao = const [], this.marcarAnosSemDados = false})
    : _anos = anos;
  final List<({int ano, double valor})> _anos;

  List<({int ano, double valor})> get anos => _anos;

  List<int> get anosSemDados {
    if (!marcarAnosSemDados || _anos.length < 2) return const [];
    final tem = {for (final a in _anos) a.ano};
    return [
      for (var a = _anos.first.ano; a <= _anos.last.ano; a++)
        if (!tem.contains(a)) a,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final faltam = anosSemDados;
    final anos = faltam.isEmpty
        ? _anos
        : ([..._anos, for (final a in faltam) (ano: a, valor: double.nan)]..sort((x, y) => x.ano.compareTo(y.ano)));
    final porAno = {for (final v in inflacao) v.ano: v};
    final comInflacao = porAno.isNotEmpty;
    final maximo = [..._anos.map((a) => a.valor), ...inflacao.map((v) => v.corrigido)].reduce((a, b) => a > b ? a : b);
    final largura = comInflacao ? 14.0 : 28.0;

    Color corGasto(int ano) {
      final v = porAno[ano];
      if (v == null) return tema.hintColor; // ano-base
      return Veredito.de(v.acimaPct).cor;
    }

    final grafico = SizedBox(
      height: 160,
      child: BarChart(
        BarChartData(
          maxY: maximo * 1.15,
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              fitInsideVertically: true,
              fitInsideHorizontally: true,
              getTooltipItem: (g, _, rod, i) {
                if (anos[g.x].valor.isNaN) return null;
                final rotulo = !comInflacao ? '' : i == 0 ? 'Gasto\n' : 'Só com a inflação\n';
                return BarTooltipItem('$rotulo${reais(rod.toY)}', const TextStyle(color: Colors.white));
              },
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 72,
                getTitlesWidget: (v, meta) => v == meta.max || v == 0
                    ? const SizedBox()
                    : Text(
                        reaisEixo(v),
                        softWrap: false,
                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                      ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  final a = anos[v.toInt()].ano;
                  if (faltam.contains(a)) {
                    return Text('$a', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor));
                  }
                  return Text(porAno[a]?.parcial == true ? '$a*' : '$a', style: tema.textTheme.bodySmall);
                },
              ),
            ),
          ),
          barGroups: [
            for (var i = 0; i < anos.length; i++)
              if (anos[i].valor.isNaN)
                BarChartGroupData(
                  x: i,
                  barRods: [BarChartRodData(toY: 0, width: largura, color: Colors.transparent)],
                )
              else
                BarChartGroupData(
                  x: i,
                  barsSpace: 3,
                  barRods: [
                    BarChartRodData(
                      toY: anos[i].valor,
                      width: largura,
                      color: comInflacao ? corGasto(anos[i].ano) : tema.colorScheme.primary,
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                    ),
                    if (porAno[anos[i].ano] != null)
                      BarChartRodData(
                        toY: porAno[anos[i].ano]!.corrigido,
                        width: largura,
                        color: tema.hintColor.withValues(alpha: 0.12),
                        borderSide: BorderSide(color: tema.hintColor, width: 1.5),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                      ),
                  ],
                ),
          ],
        ),
      ),
    );
    final aviso = faltam.isEmpty
        ? null
        : Text(
            'Sem dados publicados para ${faltam.length == 1 ? faltam.first : '${faltam.sublist(0, faltam.length - 1).join(', ')} e ${faltam.last}'}.',
            style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
          );
    if (!comInflacao) {
      return aviso == null
          ? grafico
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [grafico, const SizedBox(height: 8), aviso],
            );
    }

    Widget legenda(Color cor, String texto, {bool contorno = false}) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: contorno ? cor.withValues(alpha: 0.12) : cor,
            border: contorno ? Border.all(color: cor, width: 1.5) : null,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 6),
        Text(texto, style: tema.textTheme.bodySmall),
      ],
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        grafico,
        const SizedBox(height: 10),
        Wrap(
          spacing: 16,
          runSpacing: 6,
          children: [
            legenda(tema.hintColor, 'Ano-base (${inflacao.first.anoBase ?? anos.first.ano})'),
            legenda(Adw.amarelo, 'Gastou acima da inflação'),
            legenda(Adw.azul, 'Gastou abaixo da inflação'),
            legenda(tema.hintColor, 'Só com a inflação', contorno: true),
            if (inflacao.any((v) => v.parcial))
              Text('* ano em andamento', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
          ],
        ),
      ],
    );
  }
}

/// "Por categoria": lista o total de cada categoria e, ao tocar, compara a
/// categoria entre os anos ou entre os meses de um ano.
class _PorCategoria extends StatelessWidget {
  final Gastos g;
  const _PorCategoria(this.g);

  @override
  Widget build(BuildContext context) {
    final podeComparar = g.categoriasPorAno.length > 1 || g.categoriasPorMes.isNotEmpty;
    return ExpansionTile(
      title: const Text('Por categoria'),
      subtitle: podeComparar ? const Text('Toque numa categoria para comparar anos e meses') : null,
      shape: const Border(),
      children: [
        for (final c in g.porCategoria.take(8))
          Linha(
            titulo: nomeLegivel(c.nome),
            valor: reaisCurto(c.valor),
            aoTocar: podeComparar
                ? () => showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    showDragHandle: true,
                    builder: (_) => _CompararCategoria(g: g, categoria: c.nome),
                  )
                : null,
          ),
      ],
    );
  }
}

class _CompararCategoria extends StatefulWidget {
  final Gastos g;
  final String categoria;
  const _CompararCategoria({required this.g, required this.categoria});

  @override
  State<_CompararCategoria> createState() => _CompararCategoriaState();
}

class _CompararCategoriaState extends State<_CompararCategoria> {
  late bool porMes;
  late int ano;

  Gastos get g => widget.g;

  List<int> get anos => {...g.categoriasPorAno.keys, ...g.categoriasPorMes.keys}.toList()..sort();
  List<int> get anosComMeses => g.categoriasPorMes.keys.toList()..sort();

  double totalAno(int a) {
    final meses = g.categoriasPorMes[a]?[widget.categoria];
    if (meses != null) return meses.fold(0.0, (x, y) => x + y);
    for (final c in g.categoriasPorAno[a] ?? const <NomeValor>[]) {
      if (c.nome == widget.categoria) return c.valor;
    }
    return 0;
  }

  @override
  void initState() {
    super.initState();
    porMes = anos.length < 2 && anosComMeses.isNotEmpty;
    ano = anosComMeses.isEmpty ? anos.last : anosComMeses.last;
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final List<({String rotulo, double valor})> barras = porMes
        ? [
            for (var m = 0; m < 12; m++)
              (rotulo: mesesCurtos[m], valor: g.categoriasPorMes[ano]?[widget.categoria]?[m] ?? 0),
          ]
        : [for (final a in anos) (rotulo: '$a', valor: totalAno(a))];
    final total = barras.fold(0.0, (x, b) => x + b.valor);
    final comValor = barras.where((b) => b.valor > 0).toList();

    // Ano em andamento: comparar com um ano inteiro engana, então só avisa.
    final parciais = {for (final v in g.vsInflacao) if (v.parcial) '${v.ano}': v.meses};
    String variacao(int i) {
      if (!porMes && parciais.containsKey(barras[i].rotulo)) {
        return 'Ano em andamento (${intervaloMeses(1, parciais[barras[i].rotulo]!)})';
      }
      if (i == 0 || barras[i - 1].valor == 0 || barras[i].valor == 0) return '';
      final pct = (barras[i].valor / barras[i - 1].valor - 1) * 100;
      return '${porcentagem(pct, sinal: true)} vs ${barras[i - 1].rotulo}';
    }

    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: Adw.larguraMax),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    nomeLegivel(widget.categoria),
                    style: tema.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  if (anosComMeses.isNotEmpty && anos.length > 1)
                    SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment(value: false, label: Text('Por ano')),
                        ButtonSegment(value: true, label: Text('Por mês')),
                      ],
                      selected: {porMes},
                      onSelectionChanged: (v) => setState(() => porMes = v.first),
                    ),
                  if (porMes && anosComMeses.length > 1) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final a in anosComMeses)
                          ChoiceChip(label: Text('$a'), selected: a == ano, onSelected: (_) => setState(() => ano = a)),
                      ],
                    ),
                  ],
                  const SizedBox(height: 16),
                  if (total == 0)
                    Text(
                      'Nenhum gasto nesta categoria no período.',
                      style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor),
                    )
                  else ...[
                    SizedBox(
                      height: 160,
                      child: BarChart(
                        BarChartData(
                          maxY: barras.map((b) => b.valor).reduce((a, b) => a > b ? a : b) * 1.15,
                          gridData: const FlGridData(show: false),
                          borderData: FlBorderData(show: false),
                          barTouchData: BarTouchData(
                            touchTooltipData: BarTouchTooltipData(
                              fitInsideVertically: true,
                              fitInsideHorizontally: true,
                              getTooltipItem: (g, _, rod, _) =>
                                  BarTooltipItem(reais(rod.toY), const TextStyle(color: Colors.white)),
                            ),
                          ),
                          titlesData: FlTitlesData(
                            topTitles: const AxisTitles(),
                            rightTitles: const AxisTitles(),
                            leftTitles: AxisTitles(
                              sideTitles: SideTitles(
                                showTitles: true,
                                reservedSize: 72,
                                getTitlesWidget: (v, meta) => v == meta.max || v == 0
                                    ? const SizedBox()
                                    : Text(
                                        reaisEixo(v),
                                        softWrap: false,
                                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                                      ),
                              ),
                            ),
                            bottomTitles: AxisTitles(
                              sideTitles: SideTitles(
                                showTitles: true,
                                getTitlesWidget: (v, _) =>
                                    Text(!porMes && parciais.containsKey(barras[v.toInt()].rotulo) ? '${barras[v.toInt()].rotulo}*' : barras[v.toInt()].rotulo, style: tema.textTheme.bodySmall),
                              ),
                            ),
                          ),
                          barGroups: [
                            for (var i = 0; i < barras.length; i++)
                              BarChartGroupData(
                                x: i,
                                barRods: [
                                  BarChartRodData(
                                    toY: barras[i].valor,
                                    width: porMes ? 14 : 28,
                                    color: tema.colorScheme.primary,
                                    borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Card(
                      child: Column(
                        children: [
                          for (var i = 0; i < barras.length; i++)
                            if (barras[i].valor > 0 || !porMes)
                              Linha(
                                titulo: porMes ? '${barras[i].rotulo}/$ano' : barras[i].rotulo,
                                subtitulo: variacao(i).isEmpty ? null : variacao(i),
                                valor: reais(barras[i].valor),
                              ),
                          Linha(
                            titulo: porMes ? 'Total em $ano' : 'Total no período',
                            subtitulo: porMes ? '${comValor.length} meses com gasto' : null,
                            valor: reais(total),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Valores sem correção pela inflação.',
                      style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SecaoVotacoes extends StatelessWidget {
  final Perfil p;
  final Api api;
  const _SecaoVotacoes(this.p, this.api);

  @override
  Widget build(BuildContext context) {
    if (p.votacoes.isEmpty) {
      return Grupo(titulo: 'Votações', filhos: [SemDados(p.resumo, detalhe: 'Nenhuma votação nominal registrada')]);
    }
    final total = p.totalVotacoes;
    final pct = total == 0 ? 0 : p.participou / total * 100;
    final ordem = ['sim', 'nao', 'abstencao', 'obstrucao', 'ausente', 'licenca', 'missao', 'presidente', 'presente_sem_voto', 'outro'];
    return Grupo(
      titulo: 'Votações',
      descricao: 'Votações nominais em que o voto de cada parlamentar é registrado. '
          'Quando a esquerda (PT, PSOL e PCdoB) e a direita (PL e NOVO) votam de lados opostos, '
          'mostramos com qual dos dois o voto coincidiu, seja qual for.',
      acao: TextButton(
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TodasVotacoes(p, api: api))),
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
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final dividida = v.ladoSim != null;
    return ListTile(
      title: Text(v.proposicao ?? v.descricao ?? 'Votação de ${data(v.data)}'),
      subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text([data(v.data), if (v.resultado != null) v.resultado!, if (v.ementa != null) v.ementa!].join(' · ')),
        if (dividida || v.atencao != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Wrap(spacing: 6, runSpacing: 4, children: [
              if (dividida) Etiqueta(rotuloLado(v), v.ladoDoVoto == null ? tema.hintColor : Adw.corLado(v.ladoDoVoto!)),
              if (v.atencao != null) Etiqueta(v.atencao!, Adw.amarelo),
            ]),
          ),
      ]),
      trailing: EtiquetaVoto(v.voto),
      onTap: v.link == null ? null : () => _abrir(v.link),
    );
  }
}

/// Rótulo de uma votação em que esquerda e direita se dividiram. É o mesmo
/// texto para os dois lados, na cor de cada lado: só muda o nome do lado.
String rotuloLado(VotoEmVotacao v) {
  final lado = v.ladoDoVoto;
  if (lado == null) return 'Esquerda e direita votaram diferente';
  return 'Votou como a $lado';
}

class TodasVotacoes extends StatefulWidget {
  final Perfil p;
  final Api api;
  final bool soAtencao;
  const TodasVotacoes(this.p, {super.key, required this.api, this.soAtencao = false});

  @override
  State<TodasVotacoes> createState() => _TodasVotacoesState();
}

class _TodasVotacoesState extends State<TodasVotacoes> {
  late final List<VotoEmVotacao> _base =
      widget.soAtencao ? widget.p.votacoes.where((v) => v.atencao != null).toList() : widget.p.votacoes;
  late final Future<List<VotoEmVotacao>> _lista = widget.api.completarVotos(_base);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.soAtencao ? 'Votações que merecem atenção' : 'Votações de ${widget.p.resumo.nome}')),
      body: FutureBuilder<List<VotoEmVotacao>>(
        future: _lista,
        builder: (context, snap) {
          if (!snap.hasData && !snap.hasError) return const Center(child: CircularProgressIndicator());
          final lista = snap.data ?? _base;
          return ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 12),
            itemCount: lista.length,
            separatorBuilder: (_, _) => const Clamp(child: Divider()),
            itemBuilder: (_, i) => Clamp(child: LinhaVotacao(lista[i])),
          );
        },
      ),
    );
  }
}

/// Processos e ocorrências: só registros oficiais, cada um com a situação
/// atual e o link da fonte. Sem nota, ranking ou cor de alarme.
class _SecaoOcorrencias extends StatelessWidget {
  final Perfil p;
  const _SecaoOcorrencias(this.p);

  static const _encerradas = {'absolvido', 'arquivado', 'extinto', 'sancao_encerrada', 'informativo'};

  String _consultadas(List<FonteConsultada> fontes) {
    final nomes = fontes.map((f) => f.nome.split(':').first).toList();
    if (nomes.length <= 1) return nomes.join();
    return '${nomes.sublist(0, nomes.length - 1).join(', ')} e ${nomes.last}';
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final o = p.ocorrencias;
    const titulo = 'Processos e ocorrências';
    const descricao = 'Registros oficiais da Justiça Eleitoral, CGU, TCU e tribunais';
    if (o == null) {
      return Grupo(titulo: titulo, descricao: descricao, filhos: [
        const Linha(
          prefixo: Icon(Icons.info_outline),
          titulo: 'Sem dados',
          subtitulo: 'As fontes ainda não foram consultadas para este político.',
        ),
      ]);
    }
    final conferidas = o.fontes.where((f) => f.conferido).toList();
    final semConferir = o.fontes.where((f) => !f.conferido && f.consultadoEm != null).toList();
    return Grupo(
      titulo: titulo,
      descricao: descricao,
      filhos: [
        for (final i in o.itens)
          ListTile(
            title: Text(i.titulo),
            subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Wrap(spacing: 6, runSpacing: 4, children: [
                  Etiqueta(i.situacaoRotulo, _encerradas.contains(i.situacao) ? Colors.grey : Adw.amarelo),
                ]),
              ),
              Text([
                if (i.data != null) data(i.data),
                ?i.orgao,
                if (i.processo != null) 'Processo ${i.processo}',
              ].join(' · ')),
              if (i.descricao != null) Text(i.descricao!),
              if (i.conferencia != null)
                Text(i.conferencia!, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
            ]),
            trailing: i.link == null ? null : const Icon(Icons.open_in_new),
            onTap: i.link == null ? null : () => _abrir(i.link),
          ),
        if (o.itens.isEmpty)
          Linha(
            prefixo: const Icon(Icons.info_outline),
            titulo: conferidas.isEmpty ? 'Não foi possível conferir' : 'Nada encontrado nas fontes consultadas',
            subtitulo: conferidas.isEmpty
                ? 'A candidatura deste político não foi localizada no TSE.'
                : 'Conferido em: ${_consultadas(conferidas)}. '
                    'Isso não quer dizer que não existam processos em outros tribunais.',
          ),
        if (semConferir.isNotEmpty)
          Linha(
            prefixo: const Icon(Icons.help_outline),
            titulo: 'Não conferido em ${_consultadas(semConferir)}',
            subtitulo: 'Para não confundir com homônimos, esses cadastros só são cruzados quando o CPF '
                'da candidatura no TSE confere. Não foi possível fazer essa conferência para este político.',
          ),
        if (o.certidoes.isNotEmpty)
          ExpansionTile(
            title: const Text('Certidões criminais entregues ao TSE'),
            subtitle: const Text('Todo candidato entrega; podem ser negativas ou positivas'),
            shape: const Border(),
            children: [
              for (final c in o.certidoes)
                Linha(titulo: c.titulo, subtitulo: c.descricao, aoTocar: c.link == null ? null : () => _abrir(c.link)),
            ],
          ),
        ExpansionTile(
          title: const Text('Fontes consultadas'),
          shape: const Border(),
          children: [
            for (final f in o.fontes)
              Linha(
                titulo: f.nome,
                subtitulo: f.consultadoEm == null
                    ? 'Não consultada nesta atualização'
                    : '${f.conferido ? 'Conferido' : 'Não conferido'} · consultado em ${data(f.consultadoEm)}',
                aoTocar: f.link == null ? null : () => _abrir(f.link),
              ),
          ],
        ),
        if (o.aviso != null)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(o.aviso!, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
          ),
      ],
    );
  }
}

class _SecaoGabinete extends StatelessWidget {
  final Perfil p;
  const _SecaoGabinete(this.p);

  @override
  Widget build(BuildContext context) {
    final verba = p.verbaGabinete;
    if (p.gabinete.isEmpty && verba == null) {
      return Grupo(titulo: 'Gabinete', filhos: [SemDados(p.resumo, detalhe: 'Equipe e custo do gabinete')]);
    }
    final custo = p.custoGabinete;
    final anoVerba = verba?.ultimoAno;
    return Grupo(
      titulo: 'Gabinete',
      descricao: p.gabinete.isEmpty ? null : '${p.gabinete.length} pessoas trabalham no gabinete',
      filhos: [
        if (custo != null)
          Linha(
            titulo: 'Custo mensal com salários',
            subtitulo: custo.origem == 'verba_gabinete'
                ? 'Verba de gabinete gasta em ${mesAno(custo.referencia)}'
                : 'Soma bruta de ${custo.pessoasComValor} de ${custo.pessoas} pessoas'
                    '${custo.referencia == null ? '' : ' · folha de ${mesAno(custo.referencia)}'}',
            valor: reais(custo.mensal),
          ),
        if (custo == null && p.gabinete.isNotEmpty) SemDados(p.resumo, detalhe: 'Salário de cada pessoa do gabinete'),
        if (verba != null && anoVerba != null)
          ExpansionTile(
            title: Text('Verba de gabinete gasta em $anoVerba'),
            subtitle: Text(reais(verba.anos[anoVerba]!.total)),
            shape: const Border(),
            children: [
              if (verba.porAno.length > 1)
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 16, 16, 8),
                  child: _GraficoAnos(verba.porAno, marcarAnosSemDados: true),
                ),
              for (final m in verba.anos[anoVerba]!.porMes) Linha(titulo: _nomeMes(m.mes), valor: reais(m.valor)),
            ],
          ),
        if (p.gabinete.isNotEmpty || p.gabineteAnteriores.isNotEmpty) _Equipe(p),
      ],
    );
  }
}

/// "Ver equipe", com abas para quem está no gabinete hoje e quem já saiu.
class _Equipe extends StatefulWidget {
  final Perfil p;
  const _Equipe(this.p);

  @override
  State<_Equipe> createState() => _EquipeState();
}

class _EquipeState extends State<_Equipe> {
  bool anteriores = false;

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final p = widget.p;
    final lista = anteriores ? p.gabineteAnteriores : p.gabinete;
    return ExpansionTile(
      title: const Text('Ver equipe'),
      shape: const Border(),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
          child: SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, label: Text('Atual (${p.gabinete.length})')),
              ButtonSegment(value: true, label: Text('Já saíram (${p.gabineteAnteriores.length})')),
            ],
            selected: {anteriores},
            onSelectionChanged: (v) => setState(() => anteriores = v.first),
          ),
        ),
        if (anteriores)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: Text(
              'A fonte oficial só lista quem está no gabinete hoje. O AraraGov guarda a lista a cada coleta '
              'semanal desde novembro de 2026; a data de saída é a da coleta em que a pessoa deixou de aparecer.',
              style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
            ),
          ),
        if (lista.isEmpty)
          Linha(titulo: anteriores ? 'Ninguém saiu desde o início do acompanhamento' : 'Nenhuma pessoa na equipe hoje'),
        for (final a in lista)
          Linha(
            titulo: nomePessoa(a.nome),
            subtitulo: [
              a.nivel ?? a.cargo,
              if (anteriores)
                '${a.desde == null ? 'entrada não informada' : data(a.desde)} até ${data(a.ate)}'
              else if (a.desde != null)
                'desde ${data(a.desde)}',
            ].whereType<String>().join(' · '),
            valor: a.remuneracao == null ? null : reais(a.remuneracao),
          ),
      ],
    );
  }
}

const _mesesExtenso = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];
String _nomeMes(int m) => m >= 1 && m <= 12 ? _mesesExtenso[m - 1] : '$m';

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


/// Governador e vice não votam em plenário.
/// Nome da verba de gastos do mandato conforme o cargo.
String rotuloGastos(PoliticoResumo r) => executivo(r)
    ? 'Gastos'
    : r.esfera == 'estadual'
        ? 'Gastos de gabinete'
        : 'Gastos da cota parlamentar';

bool executivo(PoliticoResumo r) => r.cargo == 'Governador' || r.cargo == 'Vice-governador';

/// Linha mostrada quando falta um dado: diz que não há dados e qual órgão
/// é o responsável por publicá-los, sem afirmar o motivo da falta.
class SemDados extends StatelessWidget {
  final PoliticoResumo r;
  final String? detalhe;
  const SemDados(this.r, {super.key, this.detalhe});

  @override
  Widget build(BuildContext context) {
    final esfera = switch (r.esfera) {
      'federal' => 'esfera federal',
      'estadual' => 'esfera estadual',
      'municipal' => 'esfera municipal',
      _ => null,
    };
    final responsavel = r.orgao.isEmpty ? null : 'Responsável por publicar: ${r.orgao}${esfera == null ? '' : ' ($esfera)'}';
    return Linha(
      prefixo: const Icon(Icons.info_outline),
      titulo: 'Sem dados',
      subtitulo: [?detalhe, ?responsavel].join('\n'),
    );
  }
}
