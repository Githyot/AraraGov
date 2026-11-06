import 'package:flutter/material.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import 'analises.dart';
import 'perfil.dart';

/// Quantas pessoas cabem numa comparação sem poluir a tela: uma para cada
/// cor que não se confunde com outra coisa no app.
const maxComparados = 4;

/// Escolhe outro político e abre a comparação.
Future<void> abrirComparacao(BuildContext context, Api api, Perfil primeiro) async {
  final escolhido = await Navigator.of(context).push<PoliticoResumo>(
    MaterialPageRoute(builder: (_) => EscolherPolitico(api: api, excluir: {primeiro.resumo.id})),
  );
  if (escolhido == null || !context.mounted) return;
  await Navigator.of(context).push(
    MaterialPageRoute(builder: (_) => ComparacaoTela(api: api, primeiro: primeiro, idSegundo: escolhido.id)),
  );
}

class EscolherPolitico extends StatefulWidget {
  final Api api;
  final Set<String> excluir;
  const EscolherPolitico({super.key, required this.api, required this.excluir});

  @override
  State<EscolherPolitico> createState() => _EscolherPoliticoState();
}

class _EscolherPoliticoState extends State<EscolherPolitico> {
  late final Future<List<PoliticoResumo>> _lista = widget.api.politicos();
  final _busca = TextEditingController();

  @override
  void initState() {
    super.initState();
    _busca.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _busca.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Comparar com…')),
      body: FutureBuilder<List<PoliticoResumo>>(
        future: _lista,
        builder: (context, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final termo = semAcento(_busca.text.trim().toLowerCase());
          final itens = snap.data!
              .where((p) => !widget.excluir.contains(p.id) && p.emExercicio)
              .where((p) => termo.isEmpty ||
                  semAcento('${p.nome} ${p.partido ?? ''} ${p.uf ?? ''} ${p.cargo}'.toLowerCase()).contains(termo))
              .toList();
          return Clamp(
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.all(12),
                child: TextField(
                  controller: _busca,
                  autofocus: true,
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Buscar por nome, partido ou estado'),
                ),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: itens.length,
                  itemBuilder: (context, i) {
                    final p = itens[i];
                    return ListTile(
                      leading: Avatar(url: p.foto, nome: p.nome),
                      title: Text(p.nome),
                      subtitle: Text('${p.cargo} · ${p.partidoUf}'),
                      onTap: () => Navigator.of(context).pop(p),
                    );
                  },
                ),
              ),
            ]),
          );
        },
      ),
    );
  }
}

/// Em quantas votações em comum os dois votaram igual (só sim e não contam),
/// e de que ano a que ano são essas votações.
({int comuns, int iguais, int? de, int? ate})? concordancia(Perfil a, Perfil b) {
  const validos = {'sim', 'nao'};
  final votosB = {for (final v in b.votacoes) if (validos.contains(v.voto)) v.id: v.voto};
  var comuns = 0, iguais = 0;
  final anos = <int>[];
  for (final v in a.votacoes) {
    final outro = votosB[v.id];
    if (outro == null || !validos.contains(v.voto)) continue;
    comuns++;
    if (outro == v.voto) iguais++;
    final ano = _ano(v.data);
    if (ano != null) anos.add(ano);
  }
  if (comuns == 0) return null;
  anos.sort();
  return (comuns: comuns, iguais: iguais, de: anos.firstOrNull, ate: anos.lastOrNull);
}

int? _ano(String? iso) => iso == null || iso.length < 4 ? null : int.tryParse(iso.substring(0, 4));

/// "2019–2026", "2024" ou null.
String? faixaAnos(int? de, int? ate) {
  if (de == null || ate == null) return null;
  return de == ate ? '$de' : '$de–$ate';
}

String? _faixaPorAno(Perfil p, List<({int ano, double valor})> porAno) {
  if (p.ano != null) return '${p.ano}';
  final anos = [for (final a in porAno) if (a.valor != 0) a.ano]..sort();
  return faixaAnos(anos.firstOrNull, anos.lastOrNull);
}

String? _faixaVotacoes(Perfil p) {
  final anos = [for (final v in p.votacoes) ?_ano(v.data)]..sort();
  return faixaAnos(anos.firstOrNull, anos.lastOrNull);
}

/// Uma pessoa na comparação, com a cor fixa que recebeu ao entrar.
typedef Comparado = ({Perfil perfil, int cor});

class ComparacaoTela extends StatefulWidget {
  final Api api;
  final Perfil primeiro;
  final String idSegundo;
  const ComparacaoTela({super.key, required this.api, required this.primeiro, required this.idSegundo});

  @override
  State<ComparacaoTela> createState() => _ComparacaoTelaState();
}

class _ComparacaoTelaState extends State<ComparacaoTela> {
  late final List<Comparado> _pessoas = [(perfil: widget.primeiro, cor: 0)];
  Object? _erroInicial;
  bool _carregando = true;

  @override
  void initState() {
    super.initState();
    _carregar(widget.idSegundo).catchError((Object e) {
      if (mounted) setState(() => _erroInicial = e);
    });
  }

  /// Primeira cor da paleta que ninguém está usando: quem continua na tela
  /// mantém a sua cor quando outra pessoa sai.
  int _corLivre() {
    final usadas = {for (final p in _pessoas) p.cor};
    return List.generate(Adw.pessoas.length, (i) => i).firstWhere((i) => !usadas.contains(i), orElse: () => 0);
  }

  Future<void> _carregar(String id) async {
    setState(() => _carregando = true);
    try {
      // Quem entra segue o mesmo filtro de ano do perfil de onde a comparação saiu.
      final perfil = (await widget.api.perfil(id)).noAno(widget.primeiro.ano);
      if (!mounted) return;
      setState(() => _pessoas.add((perfil: perfil, cor: _corLivre())));
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  Future<void> _adicionar() async {
    final escolhido = await Navigator.of(context).push<PoliticoResumo>(
      MaterialPageRoute(
        builder: (_) => EscolherPolitico(api: widget.api, excluir: {for (final p in _pessoas) p.perfil.resumo.id}),
      ),
    );
    if (escolhido == null || !mounted) return;
    try {
      await _carregar(escolhido.id);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Não foi possível carregar ${escolhido.nome}')));
    }
  }

  void _remover(Comparado p) => setState(() => _pessoas.remove(p));

  @override
  Widget build(BuildContext context) {
    final Widget corpo;
    if (_erroInicial != null) {
      corpo = StatusPage(mascote: 'sad', titulo: 'Não foi possível carregar', descricao: '$_erroInicial');
    } else if (_pessoas.length < 2 && _carregando) {
      corpo = const Center(child: CircularProgressIndicator());
    } else {
      corpo = _Conteudo(
        _pessoas,
        carregando: _carregando,
        aoAdicionar: _pessoas.length < maxComparados ? _adicionar : null,
        aoRemover: _pessoas.length > 2 ? _remover : null,
      );
    }
    return Scaffold(appBar: AppBar(title: const Text('Comparação')), body: corpo);
  }
}

class _Conteudo extends StatelessWidget {
  final List<Comparado> pessoas;
  final bool carregando;
  final VoidCallback? aoAdicionar;
  final void Function(Comparado)? aoRemover;
  const _Conteudo(this.pessoas, {required this.carregando, this.aoAdicionar, this.aoRemover});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final brilho = tema.brightness;
    Color cor(Comparado p) => Adw.pessoa(p.cor, brilho);

    final pares = [
      for (var i = 0; i < pessoas.length; i++)
        for (var j = i + 1; j < pessoas.length; j++)
          if (concordancia(pessoas[i].perfil, pessoas[j].perfil) case final c?) (a: pessoas[i], b: pessoas[j], c: c),
    ];

    // Cada métrica vira uma linha por pessoa: valor, período e, quando é
    // número, uma barra proporcional ao maior valor da comparação.
    _Metrica numerica(String titulo, ({double? valor, String texto, String? periodo}) Function(Perfil) f) {
      final vals = [for (final p in pessoas) f(p.perfil)];
      final maior = vals.map((v) => v.valor ?? 0).fold<double>(0, (a, b) => b > a ? b : a);
      return _Metrica(titulo, [
        for (var i = 0; i < pessoas.length; i++)
          _Valor(
            pessoa: pessoas[i].perfil,
            cor: cor(pessoas[i]),
            texto: vals[i].texto,
            periodo: vals[i].periodo,
            fracao: maior > 0 && vals[i].valor != null ? vals[i].valor! / maior : null,
          ),
      ]);
    }

    _Metrica texto(String titulo, ({String texto, String? periodo}) Function(Perfil) f) => _Metrica(titulo, [
          for (final p in pessoas)
            _Valor(pessoa: p.perfil, cor: cor(p), texto: f(p.perfil).texto, periodo: f(p.perfil).periodo),
        ]);

    final rotulosGastos = {for (final p in pessoas) rotuloGastos(p.perfil.resumo)};
    final tituloGastos = rotulosGastos.length == 1 ? rotulosGastos.single : 'Gastos do mandato';

    return ListView(padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 12), children: [
      Clamp(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 12,
            runSpacing: 16,
            children: [
              for (final p in pessoas)
                _Pessoa(p.perfil, cor: cor(p), aoRemover: aoRemover == null ? null : () => aoRemover!(p)),
            ],
          ),
          const SizedBox(height: 16),
          Center(
            child: carregando
                ? const Padding(padding: EdgeInsets.all(8), child: SizedBox.square(dimension: 24, child: CircularProgressIndicator(strokeWidth: 3)))
                : aoAdicionar == null
                    ? Text('Até $maxComparados pessoas por comparação',
                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor))
                    : OutlinedButton.icon(
                        onPressed: aoAdicionar,
                        icon: const Icon(Icons.person_add_alt_1_outlined),
                        label: const Text('Adicionar político'),
                      ),
          ),
          const SizedBox(height: 24),
          if (pessoas.first.perfil.ano != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text('Mostrando só ${pessoas.first.perfil.ano}',
                  textAlign: TextAlign.center, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
            ),
          if (pares.isNotEmpty)
            Grupo(
              titulo: 'Votos em comum',
              descricao: pessoas.length == 2
                  ? 'Contam só as votações em que os dois votaram sim ou não'
                  : 'Para cada dupla, contam só as votações em que as duas pessoas votaram sim ou não',
              filhos: [
                for (final par in pares)
                  Linha(
                    prefixo: _DuasCores(cor(par.a), cor(par.b)),
                    titulo: pessoas.length == 2
                        ? 'Votaram igual'
                        : '${primeiroNome(par.a.perfil)} e ${primeiroNome(par.b.perfil)}',
                    subtitulo: [
                      '${par.c.iguais} de ${par.c.comuns} votações',
                      ?faixaAnos(par.c.de, par.c.ate),
                    ].join(' · '),
                    valor: porcentagem(100 * par.c.iguais / par.c.comuns),
                  ),
              ],
            ),
          Grupo(titulo: 'Lado a lado', filhos: [
            texto('Partido', (p) => (texto: p.resumo.partido ?? '—', periodo: 'atual')),
            texto('Posição nas votações', (p) => (
                  texto: p.posicao == null
                      ? '—'
                      : '${rotuloFaixa(p.posicao!.faixa)} (${porcentagem(p.posicao!.pctEsquerda)} esq.)',
                  // A posição é sempre calculada sobre todo o período, mesmo com filtro de ano.
                  periodo: p.posicao == null
                      ? null
                      : [p.ano == null ? _faixaVotacoes(p) : 'todo o período', '${p.posicao!.votacoes} votações']
                          .whereType<String>()
                          .join(' · '),
                )),
            numerica('Participação nas votações', (p) => (
                  valor: p.totalVotacoes == 0 ? null : 100 * p.participou / p.totalVotacoes,
                  texto: p.totalVotacoes == 0 ? '—' : porcentagem(100 * p.participou / p.totalVotacoes),
                  periodo: p.totalVotacoes == 0
                      ? null
                      : [?_faixaVotacoes(p), '${p.totalVotacoes} votações'].join(' · '),
                )),
            numerica(pessoas.any((p) => p.perfil.salario.teto) ? 'Salário mensal (ou teto)' : 'Salário mensal', (p) => (
                  valor: p.salario.atual,
                  texto: reais(p.salario.atual),
                  periodo: p.salario.atual == null || p.salario.historico.isEmpty
                      ? null
                      : 'desde ${mesAno(p.salario.historico.last.desde)}',
                )),
            texto('Doação do salário', (p) => (texto: p.doacaoSalario?.titulo ?? 'Não declarada', periodo: null)),
            numerica('$tituloGastos (soma do período)', (p) => (
                  valor: p.gastos.total == 0 ? null : p.gastos.total,
                  texto: p.gastos.total == 0 ? 'Sem dados' : reais(p.gastos.total),
                  periodo: p.gastos.total == 0 ? null : _faixaPorAno(p, p.gastos.porAno),
                )),
            numerica('Custo mensal do gabinete', (p) {
              final c = p.custoGabinete;
              return (
                valor: c?.mensal,
                texto: c == null ? 'Sem dados' : reais(c.mensal),
                periodo: c?.referencia == null
                    ? null
                    : '${c!.origem == 'verba_gabinete' ? 'verba gasta em' : 'folha de'} ${mesAno(c.referencia)}',
              );
            }),
            numerica('Emendas indicadas (soma do período)', (p) => (
                  valor: p.emendas?.totalEmpenhado,
                  texto: p.emendas == null ? 'Sem dados' : reais(p.emendas!.totalEmpenhado),
                  periodo: p.emendas == null ? null : _faixaPorAno(p, p.emendas!.porAno),
                )),
            numerica('Emendas pagas (soma do período)', (p) => (
                  valor: p.emendas?.totalPago,
                  texto: p.emendas == null ? 'Sem dados' : reais(p.emendas!.totalPago),
                  periodo: p.emendas == null ? null : _faixaPorAno(p, p.emendas!.porAno),
                )),
          ]),
          Text(
            'Embaixo de cada valor está o período a que ele se refere. Os períodos variam porque cada '
            'pessoa tem mandatos e fontes diferentes, e cargos e casas diferentes têm regras e verbas diferentes.',
            style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    ]);
  }
}

/// Primeiro nome de urna, para rótulos curtos ("Kim", "AJ").
String primeiroNome(Perfil p) => p.resumo.nome.split(' ').first;

/// Foto com anel na cor da pessoa, nome e, se puder sair, o botão de remover.
class _Pessoa extends StatelessWidget {
  final Perfil p;
  final Color cor;
  final VoidCallback? aoRemover;
  const _Pessoa(this.p, {required this.cor, this.aoRemover});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return SizedBox(
      width: 168,
      child: Stack(children: [
        Column(children: [
          Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: cor, width: 3)),
            child: Avatar(url: p.resumo.foto, nome: p.resumo.nome, tamanho: 64),
          ),
          const SizedBox(height: 8),
          Text(p.resumo.nome,
              textAlign: TextAlign.center,
              style: tema.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: cor)),
          Text('${p.resumo.cargo} · ${p.resumo.partidoUf}',
              textAlign: TextAlign.center, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
        ]),
        if (aoRemover != null)
          Positioned(
            top: 0,
            right: 12,
            child: IconButton(
              tooltip: 'Tirar ${p.resumo.nome} da comparação',
              visualDensity: VisualDensity.compact,
              style: IconButton.styleFrom(backgroundColor: tema.colorScheme.surfaceContainer),
              icon: const Icon(Icons.close, size: 18),
              onPressed: aoRemover,
            ),
          ),
      ]),
    );
  }
}

/// Duas bolinhas sobrepostas com as cores de uma dupla.
class _DuasCores extends StatelessWidget {
  final Color a, b;
  const _DuasCores(this.a, this.b);

  @override
  Widget build(BuildContext context) {
    final fundo = Theme.of(context).colorScheme.surfaceContainer;
    Widget bola(Color c) => Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(color: c, shape: BoxShape.circle, border: Border.all(color: fundo, width: 2)),
        );
    return SizedBox(width: 28, height: 16, child: Stack(children: [bola(a), Positioned(left: 10, child: bola(b))]));
  }
}

class _Valor {
  final Perfil pessoa;
  final Color cor;
  final String texto;
  final String? periodo;
  final double? fracao;
  const _Valor({required this.pessoa, required this.cor, required this.texto, this.periodo, this.fracao});
}

/// Uma métrica com uma linha por pessoa, na cor de cada uma.
class _Metrica extends StatelessWidget {
  final String titulo;
  final List<_Valor> valores;
  const _Metrica(this.titulo, this.valores);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final estilo = tema.textTheme.bodyLarge?.copyWith(fontFeatures: const [FontFeature.tabularFigures()]);
    final dica = tema.textTheme.bodySmall?.copyWith(color: tema.hintColor);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(titulo, style: tema.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
        for (final v in valores)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(
                  padding: const EdgeInsets.only(top: 6, right: 8),
                  child: Container(width: 10, height: 10, decoration: BoxDecoration(color: v.cor, shape: BoxShape.circle)),
                ),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(v.pessoa.resumo.nome, maxLines: 1, overflow: TextOverflow.ellipsis),
                    if (v.periodo != null) Text(v.periodo!, style: dica),
                  ]),
                ),
                const SizedBox(width: 12),
                Flexible(
                  child: Align(
                    alignment: Alignment.topRight,
                    child: Text(v.texto,
                        textAlign: TextAlign.end, style: estilo?.copyWith(color: v.cor, fontWeight: FontWeight.w600)),
                  ),
                ),
              ]),
              if (v.fracao != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6, left: 18),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(99),
                    child: LinearProgressIndicator(
                      value: v.fracao!.clamp(0, 1),
                      minHeight: 6,
                      color: v.cor,
                      backgroundColor: v.cor.withValues(alpha: 0.15),
                    ),
                  ),
                ),
            ]),
          ),
      ]),
    );
  }
}
