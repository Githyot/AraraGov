part of 'municipios.dart';

/// Aba Dinheiro: resumo do ano, evolução, de onde vem e para onde vai.
class _Dinheiro extends StatefulWidget {
  final Api api;
  final String pasta, uf;
  const _Dinheiro({required this.api, required this.pasta, required this.uf});

  @override
  State<_Dinheiro> createState() => _DinheiroState();
}

class _DinheiroState extends State<_Dinheiro> {
  late final Future<List<Map<int, DocumentoMd>>> _dados = Future.wait([
    _porAno(widget.api, widget.pasta, ''),
    _porAno(widget.api, widget.pasta, '-pagamentos'),
    _porAno(widget.api, widget.pasta, '-mensal'),
  ]);
  int? _ano, _mes;
  bool _hoje = false, _porMes = false;

  @override
  Widget build(BuildContext context) => FutureBuilder<List<Map<int, DocumentoMd>>>(
        future: _dados,
        builder: (context, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final financas = snap.data![0];
          final pagamentos = snap.data![1];
          final mensais = snap.data![2];
          if (financas.isEmpty && mensais.isEmpty) {
            return const _Pagina([_SemDados(motivo: 'As contas deste município ainda não foram coletadas do Siconfi.')]);
          }
          final contas = {for (final e in financas.entries) e.key: ContasAno.de(e.key, e.value)};
          final anos = {...financas.keys, ...mensais.keys}.toList()..sort((a, b) => b.compareTo(a));
          final ano = anos.contains(_ano) ? _ano! : anos.first;
          final doc = financas[ano];
          final anual = contas[ano];
          final mensal = mensais[ano];
          final meses = mensal == null ? const <int>[] : mesesPublicados(mensal);
          final porMes = meses.isNotEmpty && (_porMes || anual == null && meses.length == 1);
          final mes = meses.contains(_mes) ? _mes! : (meses.isEmpty ? 0 : meses.last);
          final pag = pagamentos[ano];
          final fator = anual?.fatorIpca;

          // O que mostrar: um mês, o ano declarado ou, sem a declaração anual
          // (ano corrente), a soma dos meses já publicados.
          final ContasAno c;
          final String rotulo;
          ContasAno? anterior;
          String? rotuloAnterior;
          final mensalAnterior = mensais[ano - 1];
          ContasAno dosMeses(int a, DocumentoMd d, Set<int> ms) => contasDosMeses(a, d, ms,
              fatorIpca: contas[a]?.fatorIpca, ipcaAte: contas[a]?.ipcaAte, populacao: contas[a]?.populacao ?? anual?.populacao);
          if (porMes) {
            c = dosMeses(ano, mensal!, {mes});
            rotulo = '${nomesMeses[mes - 1]} de $ano';
            if (mensalAnterior != null && mesesPublicados(mensalAnterior).contains(mes)) {
              anterior = dosMeses(ano - 1, mensalAnterior, {mes});
              rotuloAnterior = 'a ${nomesMeses[mes - 1]} de ${ano - 1}';
            }
          } else if (anual != null) {
            c = anual;
            rotulo = '$ano';
            anterior = contas[ano - 1];
            rotuloAnterior = 'a ${ano - 1}';
          } else {
            c = dosMeses(ano, mensal!, meses.toSet());
            rotulo = meses.length == 12 ? '$ano' : '$ano, até ${nomesMeses[meses.last - 1]}';
            if (mensalAnterior != null && meses.every(mesesPublicados(mensalAnterior).contains)) {
              anterior = dosMeses(ano - 1, mensalAnterior, meses.toSet());
              rotuloAnterior = meses.length == 12 ? 'a ${ano - 1}' : 'ao mesmo período de ${ano - 1}';
            }
          }
          final m = _Moeda(_hoje && fator != null ? fator : 1);
          final temContas = c.arrecadado != null || c.gasto != null;
          return _Pagina([
            _Controles(
              anos: anos,
              ano: ano,
              ipcaAte: fator == null ? null : anual!.ipcaAte,
              hoje: _hoje,
              meses: meses,
              porMes: porMes,
              mes: mes,
              temAnual: anual != null,
              aoMudarAno: (a) => setState(() => _ano = a),
              aoMudarHoje: (h) => setState(() => _hoje = h),
              aoMudarPorMes: (v) => setState(() => _porMes = v),
              aoMudarMes: (v) => setState(() => _mes = v),
            ),
            if (temContas) _Resumo(c, anterior, m, rotulo: rotulo, rotuloAnterior: rotuloAnterior, mensal: porMes || anual == null),
            if (mensal != null && meses.length > 1 && (porMes || anual == null))
              _Meses(ano, mensal, meses, m, destaque: porMes ? mes : null, aoTocar: (v) => setState(() {
                _porMes = true;
                _mes = v;
              })),
            if (!porMes && anual != null && contas.values.where((x) => x.arrecadado != null || x.gasto != null).length > 1)
              _Evolucao(contas.values.toList()..sort((a, b) => a.ano.compareTo(b.ano)), destaque: ano),
            if (c.grupos.isNotEmpty) _Receitas(c, m),
            if (c.areas.isNotEmpty) _Gastos(c, porMes ? null : doc, porMes ? null : pag, m),
            if (doc != null) _SemDados(linhas: doc.tabela('sem-dados')),
            if (pag == null && !porMes) _SemDados(motivo: 'Quem recebeu cada pagamento: ${_semTce(widget.uf)}'),
            _Fonte([
              if (doc != null) 'Siconfi (Tesouro Nacional), declaração de contas anuais',
              if (mensal != null) 'Siconfi, matriz de saldos contábeis mensal',
              if (pag != null) 'pagamentos pelo ${_tribunais[widget.uf]}',
              if (fator != null) 'IPCA (IBGE, pelo Banco Central)',
            ].join('; ')),
          ]);
        },
      );
}

/// Arrecadado e gasto de cada mês do ano; tocar numa barra abre o mês.
class _Meses extends StatelessWidget {
  final int ano;
  final DocumentoMd mensal;
  final List<int> meses;
  final _Moeda m;
  final int? destaque;
  final ValueChanged<int> aoTocar;
  const _Meses(this.ano, this.mensal, this.meses, this.m, {this.destaque, required this.aoTocar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final contas = {for (final mes in meses) mes: contasDosMeses(ano, mensal, {mes})};
    double v(double? x) => (x ?? 0) * m.fator;
    final maximo = contas.values.expand((c) => [v(c.arrecadado), v(c.gasto)]).fold<double>(1, (a, b) => a > b ? a : b);
    final corArrecadado = tema.colorScheme.primary;
    const corGasto = Adw.azul;
    return Grupo(
      titulo: 'Mês a mês em $ano',
      descricao: 'Toque num mês para ver os valores dele.',
      filhos: [
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: SizedBox(
            height: 180,
            child: BarChart(BarChartData(
              minY: 0,
              maxY: maximo * 1.15,
              gridData: const FlGridData(show: false),
              borderData: FlBorderData(show: false),
              barTouchData: BarTouchData(
                touchCallback: (evento, resposta) {
                  final g = resposta?.spot?.touchedBarGroupIndex;
                  if (evento is FlTapUpEvent && g != null) aoTocar(meses[g]);
                },
                touchTooltipData: BarTouchTooltipData(
                  getTooltipItem: (g, _, rod, i) => BarTooltipItem(
                    '${i == 0 ? 'Arrecadado' : 'Gasto'}\n${reais(rod.toY)}',
                    const TextStyle(color: Colors.white),
                  ),
                ),
              ),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(),
                rightTitles: const AxisTitles(),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 64,
                    getTitlesWidget: (y, meta) => y == meta.max || y == 0
                        ? const SizedBox()
                        : Text(reaisCurto(y), style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (x, _) {
                      final mes = meses[x.toInt()];
                      return Text(nomesMeses[mes - 1].substring(0, 3),
                          style: tema.textTheme.bodySmall?.copyWith(fontWeight: mes == destaque ? FontWeight.bold : null));
                    },
                  ),
                ),
              ),
              barGroups: [
                for (var i = 0; i < meses.length; i++)
                  BarChartGroupData(x: i, barsSpace: 2, barRods: [
                    for (final (valor, cor) in [
                      (v(contas[meses[i]]!.arrecadado), corArrecadado),
                      (v(contas[meses[i]]!.gasto), corGasto),
                    ])
                      BarChartRodData(
                        toY: valor,
                        width: 8,
                        color: destaque == null || meses[i] == destaque ? cor : cor.withValues(alpha: 0.45),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
                      ),
                  ]),
              ],
            )),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
          child: Wrap(spacing: 16, runSpacing: 4, children: [
            _Legenda(corArrecadado, 'Arrecadado'),
            const _Legenda(corGasto, 'Gasto (pago)'),
          ]),
        ),
      ],
    );
  }
}

/// Formata valores do ano, corrigidos ou não pela inflação.
class _Moeda {
  final double fator;
  const _Moeda(this.fator);

  String longo(double? v) => v == null ? 'Não há dados' : reais(v * fator);
  String curto(double? v) => v == null ? '—' : reaisCurto(v * fator);
}

TextStyle? _estiloValor(BuildContext context, {bool forte = false}) => Theme.of(context).textTheme.bodyLarge?.copyWith(
      fontFeatures: const [FontFeature.tabularFigures()],
      fontWeight: forte ? FontWeight.bold : null,
    );

String _milhar(int n) => n.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');

String _comSinal(double v) => '${v < 0 ? '−' : '+'}${reaisCurto(v.abs())}';

/// Ano, ano inteiro ou mês a mês, e valores da época ou de hoje.
class _Controles extends StatelessWidget {
  final List<int> anos, meses;
  final int ano, mes;
  final String? ipcaAte;
  final bool hoje, porMes, temAnual;
  final ValueChanged<int> aoMudarAno, aoMudarMes;
  final ValueChanged<bool> aoMudarHoje, aoMudarPorMes;
  const _Controles({
    required this.anos,
    required this.ano,
    required this.ipcaAte,
    required this.hoje,
    required this.meses,
    required this.porMes,
    required this.mes,
    required this.temAnual,
    required this.aoMudarAno,
    required this.aoMudarHoje,
    required this.aoMudarPorMes,
    required this.aoMudarMes,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final dica = tema.textTheme.bodySmall?.copyWith(color: tema.hintColor);
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (anos.length > 1) _Anos(anos: anos, atual: ano, aoMudar: aoMudarAno),
        Wrap(spacing: 12, runSpacing: 8, children: [
          if (meses.isNotEmpty)
            SegmentedButton<bool>(
              showSelectedIcon: false,
              segments: [
                ButtonSegment(value: false, label: Text(temAnual || meses.length == 12 ? 'Ano inteiro' : 'Ano até agora')),
                const ButtonSegment(value: true, label: Text('Por mês')),
              ],
              selected: {porMes},
              onSelectionChanged: (s) => aoMudarPorMes(s.first),
            ),
          if (ipcaAte != null)
            SegmentedButton<bool>(
              showSelectedIcon: false,
              segments: [
                ButtonSegment(value: false, label: Text('Valores de $ano')),
                const ButtonSegment(value: true, label: Text('Valores de hoje')),
              ],
              selected: {hoje},
              onSelectionChanged: (s) => aoMudarHoje(s.first),
            ),
        ]),
        if (porMes) ...[
          const SizedBox(height: 10),
          Wrap(spacing: 6, runSpacing: 4, children: [
            for (final m in meses)
              ChoiceChip(
                label: Text(nomesMeses[m - 1].substring(0, 3)),
                selected: m == mes,
                onSelected: (_) => aoMudarMes(m),
              ),
          ]),
        ],
        if (ipcaAte != null || meses.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 6, 4, 0),
            child: Text(
              ipcaAte != null && hoje
                  ? 'Corrigidos pela inflação (IPCA) até ${mesAno(ipcaAte)}.'
                  : 'Em reais de $ano, sem correção pela inflação.',
              style: dica,
            ),
          ),
      ]),
    );
  }
}

/// Totais do ano e as relações entre eles.
class _Resumo extends StatelessWidget {
  final ContasAno c;
  final ContasAno? anterior;
  final _Moeda m;
  final String rotulo;
  final String? rotuloAnterior;

  /// Valores de um mês ou da soma dos meses (sem a declaração anual).
  final bool mensal;
  const _Resumo(this.c, this.anterior, this.m, {required this.rotulo, this.rotuloAnterior, this.mensal = false});

  @override
  Widget build(BuildContext context) {
    final gastoHab = c.porHabitante(c.gasto);
    final arrecadadoHab = c.porHabitante(c.arrecadado);
    final repasses = c.fracaoRepasses;
    final naoPago = c.naoPago;
    final ant = anterior;
    Widget? comparar(String titulo, double? Function(ContasAno) valor) {
      final v = ant == null ? null : variacao(c, ant, valor);
      if (v == null) return null;
      return Linha(
        titulo: '$titulo em relação ${rotuloAnterior ?? 'a ${ant!.ano}'}',
        subtitulo: v.real ? 'Já descontada a inflação do período (IPCA)' : 'Sem descontar a inflação',
        valor: porcentagem(v.fracao * 100, sinal: true),
      );
    }

    final variacoes = [comparar('Arrecadação', (x) => x.arrecadado), comparar('Gastos', (x) => x.gasto)].whereType<Widget>();
    return Grupo(
      titulo: 'Resumo de $rotulo',
      filhos: [
        _Totais(c, m),
        if (gastoHab != null)
          Linha(
            titulo: 'Gasto por habitante',
            subtitulo: [
              if (arrecadadoHab != null) 'Arrecadado por habitante: ${m.longo(arrecadadoHab)}',
              '${_milhar(c.populacao!)} habitantes',
            ].join('\n'),
            valor: m.longo(gastoHab),
          ),
        if (repasses != null)
          Linha(
            titulo: 'Dinheiro vindo de repasses',
            subtitulo: 'Parte da arrecadação que veio da União e do estado',
            valor: porcentagem(repasses * 100),
          ),
        if (!mensal && naoPago != null && naoPago > 0)
          Linha(
            titulo: 'Contratado e não pago no ano',
            subtitulo: 'Empenhado em ${c.ano} e deixado para pagar depois (restos a pagar)',
            valor: m.longo(naoPago),
          ),
        ...variacoes,
      ],
    );
  }
}

/// Três números grandes: arrecadado, gasto e a diferença.
class _Totais extends StatelessWidget {
  final ContasAno c;
  final _Moeda m;
  const _Totais(this.c, this.m);

  @override
  Widget build(BuildContext context) {
    final saldo = c.saldo;
    final itens = [
      _Numero('Arrecadado', m.curto(c.arrecadado), c.arrecadado == null ? null : m.longo(c.arrecadado)),
      _Numero('Gasto (pago)', m.curto(c.gasto), c.gasto == null ? null : m.longo(c.gasto)),
      _Numero(
        saldo == null || saldo >= 0 ? 'Arrecadou a mais' : 'Gastou a mais',
        saldo == null ? '—' : _comSinal(saldo * m.fator),
        saldo == null ? null : m.longo(saldo.abs()),
      ),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
      child: LayoutBuilder(
        builder: (context, limites) => limites.maxWidth < 420
            ? Column(children: [
                for (var i = 0; i < itens.length; i++) ...[if (i > 0) const SizedBox(height: 12), itens[i]],
              ])
            : Row(crossAxisAlignment: CrossAxisAlignment.start, children: [for (final i in itens) Expanded(child: i)]),
      ),
    );
  }
}

class _Numero extends StatelessWidget {
  final String rotulo, valor;
  final String? exato;
  const _Numero(this.rotulo, this.valor, this.exato);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Tooltip(
      message: exato ?? '',
      child: SizedBox(
        width: double.infinity,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(rotulo, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
          const SizedBox(height: 2),
          Text(valor,
              style: tema.textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold, fontFeatures: const [FontFeature.tabularFigures()])),
        ]),
      ),
    );
  }
}

/// Arrecadado e gasto ano a ano, em reais de hoje quando há IPCA para todos.
class _Evolucao extends StatelessWidget {
  final List<ContasAno> anos;
  final int destaque;
  const _Evolucao(this.anos, {required this.destaque});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final lista = anos.where((a) => a.arrecadado != null || a.gasto != null).toList();
    final corrigido = lista.every((a) => a.fatorIpca != null);
    double v(ContasAno a, double? x) => (x ?? 0) * (corrigido ? a.fatorIpca! : 1);
    final maximo = lista.expand((a) => [v(a, a.arrecadado), v(a, a.gasto)]).reduce((a, b) => a > b ? a : b);
    final corGasto = Adw.azul;
    final corArrecadado = tema.colorScheme.primary;
    return Grupo(
      titulo: 'Evolução',
      descricao: corrigido
          ? 'Arrecadado e gasto por ano, em reais de hoje (corrigidos pelo IPCA).'
          : 'Arrecadado e gasto por ano, sem correção pela inflação.',
      filhos: [
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: SizedBox(
            height: 180,
            child: BarChart(BarChartData(
              minY: 0,
              maxY: maximo * 1.15,
              gridData: const FlGridData(show: false),
              borderData: FlBorderData(show: false),
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipItem: (g, _, rod, i) => BarTooltipItem(
                    '${i == 0 ? 'Arrecadado' : 'Gasto'}\n${reais(rod.toY)}',
                    const TextStyle(color: Colors.white),
                  ),
                ),
              ),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(),
                rightTitles: const AxisTitles(),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 64,
                    getTitlesWidget: (y, meta) => y == meta.max || y == 0
                        ? const SizedBox()
                        : Text(reaisCurto(y), style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (x, _) {
                      final a = lista[x.toInt()].ano;
                      return Text('$a',
                          style: tema.textTheme.bodySmall?.copyWith(fontWeight: a == destaque ? FontWeight.bold : null));
                    },
                  ),
                ),
              ),
              barGroups: [
                for (var i = 0; i < lista.length; i++)
                  BarChartGroupData(x: i, barsSpace: 4, barRods: [
                    for (final (valor, cor) in [
                      (v(lista[i], lista[i].arrecadado), corArrecadado),
                      (v(lista[i], lista[i].gasto), corGasto),
                    ])
                      BarChartRodData(
                        toY: valor,
                        width: 14,
                        color: lista[i].ano == destaque ? cor : cor.withValues(alpha: 0.55),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                      ),
                  ]),
              ],
            )),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
          child: Wrap(spacing: 16, runSpacing: 4, children: [
            _Legenda(corArrecadado, 'Arrecadado'),
            _Legenda(corGasto, 'Gasto (pago)'),
          ]),
        ),
      ],
    );
  }
}

class _Legenda extends StatelessWidget {
  final Color cor;
  final String texto;
  final String? valor;
  const _Legenda(this.cor, this.texto, [this.valor]);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 10, height: 10, decoration: BoxDecoration(color: cor, borderRadius: BorderRadius.circular(3))),
      const SizedBox(width: 6),
      Text(texto, style: tema.textTheme.bodySmall),
      if (valor != null) Text(' $valor', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
    ]);
  }
}

/// Nome, valor e uma barra com a parcela do total.
class _Barra extends StatelessWidget {
  final String nome, valor;
  final double? fracao;
  final Color? cor;
  const _Barra({required this.nome, required this.valor, this.fracao, this.cor});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final f = fracao;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(child: Text(nome, style: tema.listTileTheme.titleTextStyle)),
        const SizedBox(width: 12),
        Text(valor, style: _estiloValor(context)),
      ]),
      if (f != null) ...[
        const SizedBox(height: 6),
        Row(children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: f.clamp(0, 1).toDouble(),
                minHeight: 6,
                color: cor ?? tema.colorScheme.primary,
                backgroundColor: tema.colorScheme.outlineVariant,
              ),
            ),
          ),
          SizedBox(
            width: 56,
            child: Text(porcentagem(f * 100),
                textAlign: TextAlign.end, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
          ),
        ]),
      ],
    ]);
  }
}

/// Linha com barra fora de um ExpansionTile; `seta` reserva o espaço da seta
/// para alinhar os valores com as linhas que abrem.
class _LinhaBarra extends StatelessWidget {
  final _Barra barra;
  final bool recuo, seta;
  const _LinhaBarra(this.barra, {this.recuo = false, this.seta = false});

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(recuo ? 28 : 12, 10, seta ? 52 : 12, 10),
        child: barra,
      );
}

class _Abrir extends StatelessWidget {
  final _Barra barra;
  final List<Widget> filhos;
  final bool aberto;
  const _Abrir(this.barra, this.filhos, {this.aberto = false});

  @override
  Widget build(BuildContext context) => ExpansionTile(
        shape: const Border(),
        collapsedShape: const Border(),
        initiallyExpanded: aberto,
        title: barra,
        children: filhos,
      );
}

class _Total extends StatelessWidget {
  final String nome, valor;
  const _Total(this.nome, this.valor);

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.05),
        padding: const EdgeInsets.fromLTRB(12, 14, 52, 14),
        child: Row(children: [
          Expanded(child: Text(nome, style: _estiloValor(context, forte: true))),
          Text(valor, style: _estiloValor(context, forte: true)),
        ]),
      );
}

Color _corGrupo(BuildContext context, String nome) => switch (nome) {
      nomeImpostos => Theme.of(context).colorScheme.primary,
      nomeRepasses => Adw.azul,
      _ => Adw.roxo,
    };

/// De onde vem o dinheiro: impostos da cidade, repasses e o resto.
class _Receitas extends StatelessWidget {
  final ContasAno c;
  final _Moeda m;
  const _Receitas(this.c, this.m);

  @override
  Widget build(BuildContext context) {
    final soma = c.grupos.fold<double>(0, (s, g) => s + g.total);
    final base = c.arrecadado ?? soma;
    double? fr(double v) => base > 0 ? v / base : null;
    return Grupo(
      titulo: 'De onde vem o dinheiro',
      descricao: 'Receita líquida, já sem as deduções (como a parte que vai para o Fundeb). '
          'A barra mostra a parte de cada item em tudo o que foi arrecadado.',
      filhos: [
        if (c.grupos.length > 1 && base > 0) _Composicao(c.grupos, base),
        for (final g in c.grupos)
          if (g.itens.isEmpty)
            _LinhaBarra(
              _Barra(nome: g.nome, valor: m.longo(g.total), fracao: fr(g.total), cor: _corGrupo(context, g.nome)),
              seta: true,
            )
          else
            _Abrir(
              _Barra(nome: g.nome, valor: m.longo(g.total), fracao: fr(g.total), cor: _corGrupo(context, g.nome)),
              [
                for (final i in g.itens)
                  _LinhaBarra(
                    _Barra(nome: i.nome, valor: m.longo(i.valor), fracao: fr(i.valor), cor: _corGrupo(context, g.nome)),
                    recuo: true,
                    seta: true,
                  ),
              ],
              aberto: g.nome != nomeOutras,
            ),
        _Total('Total arrecadado', m.longo(base)),
      ],
    );
  }
}

/// Barra única dividida pelos grupos de receita, com legenda.
class _Composicao extends StatelessWidget {
  final List<GrupoReceita> grupos;
  final double base;
  const _Composicao(this.grupos, this.base);

  @override
  Widget build(BuildContext context) {
    final positivos = grupos.where((g) => g.total > 0).toList();
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: SizedBox(
            height: 14,
            child: Row(children: [
              for (var i = 0; i < positivos.length; i++) ...[
                if (i > 0) const SizedBox(width: 2),
                Expanded(
                  flex: (positivos[i].total / base * 1000).round().clamp(1, 1000),
                  child: Container(color: _corGrupo(context, positivos[i].nome)),
                ),
              ],
            ]),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(spacing: 16, runSpacing: 6, children: [
          for (final g in positivos) _Legenda(_corGrupo(context, g.nome), g.nome, porcentagem(g.total / base * 100)),
        ]),
      ]),
    );
  }
}

/// Para onde vai o dinheiro: áreas (funções), com subáreas e quem recebeu.
class _Gastos extends StatelessWidget {
  final ContasAno c;
  final DocumentoMd? doc;
  final DocumentoMd? pag;
  final _Moeda m;
  const _Gastos(this.c, this.doc, this.pag, this.m);

  /// Áreas abaixo desta fração do total vão para "Outras áreas".
  static const _pequena = 0.01;

  Widget _area(BuildContext context, AreaGasto a, double total, {bool recuo = false}) {
    final barra = _Barra(nome: a.nome, valor: m.longo(a.pago), fracao: total > 0 ? a.pago / total : null);
    final subareas = (doc?.tabela('areas') ?? const <Map<String, String?>>[]).where((s) => s['funcao'] == a.funcao && s['subfuncao'] != null).toList()
      ..sort((x, y) => _n(y['pago']).compareTo(_n(x['pago'])));
    if (subareas.isEmpty) return _LinhaBarra(barra, recuo: recuo, seta: true);
    final abrir = _Abrir(barra, [for (final s in subareas) _Subarea(subarea: s, pagamentos: pag, m: m)]);
    return recuo ? Padding(padding: const EdgeInsets.only(left: 16), child: abrir) : abrir;
  }

  @override
  Widget build(BuildContext context) {
    final total = c.gasto ?? 0;
    final principais = c.areas.where((a) => total <= 0 || a.pago / total >= _pequena).toList();
    final resto = c.areas.where((a) => !principais.contains(a)).toList();
    final somaResto = resto.fold<double>(0, (s, a) => s + a.pago);
    return Grupo(
      titulo: 'Para onde vai o dinheiro',
      descricao: 'Valor pago ${doc == null ? 'no período' : 'no ano'}, por área. A barra mostra a parte de cada área no total gasto. '
          '${doc == null ? '' : 'Toque para ver as subáreas${pag == null ? '' : ' e quem recebeu'}.'}',
      filhos: [
        for (final a in principais) _area(context, a, total),
        if (resto.isNotEmpty)
          _Abrir(
            _Barra(nome: 'Outras áreas (${resto.length})', valor: m.longo(somaResto), fracao: total > 0 ? somaResto / total : null),
            [for (final a in resto) _area(context, a, total, recuo: true)],
          ),
        _Total('Total gasto (pago)', m.longo(c.gasto)),
      ],
    );
  }
}

class _Subarea extends StatelessWidget {
  final Map<String, String?> subarea;
  final DocumentoMd? pagamentos;
  final _Moeda m;
  const _Subarea({required this.subarea, this.pagamentos, required this.m});

  @override
  Widget build(BuildContext context) {
    final nome = subarea['area'] ?? '—';
    final valor = Text(m.longo(numeroMd(subarea['pago'])), style: _estiloValor(context));
    final quem = pagamentos == null
        ? const <Map<String, String?>>[]
        : pagamentos!
            .tabela('areas-favorecidos')
            .where((r) => semAcento((r['subfuncao'] ?? '').toLowerCase()) == semAcento(nome.toLowerCase()))
            .toList();
    if (quem.isEmpty) {
      return ListTile(
        contentPadding: const EdgeInsets.fromLTRB(28, 0, 52, 0),
        title: Text(nome),
        trailing: valor,
      );
    }
    return ExpansionTile(
      shape: const Border(),
      collapsedShape: const Border(),
      tilePadding: const EdgeInsets.fromLTRB(28, 0, 12, 0),
      title: Row(children: [Expanded(child: Text(nome)), const SizedBox(width: 12), valor]),
      children: [
        for (final r in quem)
          ListTile(
            contentPadding: const EdgeInsets.fromLTRB(44, 0, 52, 0),
            title: Text(r['favorecido'] ?? '—'),
            subtitle: r['cnpj'] == null ? null : Text(r['cnpj']!),
            trailing: Text(m.longo(numeroMd(r['pago'])), style: _estiloValor(context)),
          ),
      ],
    );
  }
}
