import 'package:flutter/material.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../widgets/adw.dart';
import 'analises.dart';

/// Escolhe outro político e abre a comparação lado a lado.
Future<void> abrirComparacao(BuildContext context, Api api, Perfil primeiro) async {
  final escolhido = await Navigator.of(context).push<PoliticoResumo>(
    MaterialPageRoute(builder: (_) => EscolherPolitico(api: api, excluir: primeiro.resumo.id)),
  );
  if (escolhido == null || !context.mounted) return;
  await Navigator.of(context).push(
    MaterialPageRoute(builder: (_) => ComparacaoTela(api: api, primeiro: primeiro, idSegundo: escolhido.id)),
  );
}

class EscolherPolitico extends StatefulWidget {
  final Api api;
  final String excluir;
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
              .where((p) => p.id != widget.excluir && p.emExercicio)
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

/// Em quantas votações em comum os dois votaram igual (só sim e não contam).
({int comuns, int iguais})? concordancia(Perfil a, Perfil b) {
  const validos = {'sim', 'nao'};
  final votosB = {for (final v in b.votacoes) if (validos.contains(v.voto)) v.id: v.voto};
  var comuns = 0, iguais = 0;
  for (final v in a.votacoes) {
    final outro = votosB[v.id];
    if (outro == null || !validos.contains(v.voto)) continue;
    comuns++;
    if (outro == v.voto) iguais++;
  }
  return comuns == 0 ? null : (comuns: comuns, iguais: iguais);
}

class ComparacaoTela extends StatelessWidget {
  final Api api;
  final Perfil primeiro;
  final String idSegundo;
  const ComparacaoTela({super.key, required this.api, required this.primeiro, required this.idSegundo});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Comparação')),
      body: FutureBuilder<Perfil>(
        future: api.perfil(idSegundo),
        builder: (context, snap) {
          if (snap.hasError) {
            return StatusPage(mascote: 'sad', titulo: 'Não foi possível carregar', descricao: '${snap.error}');
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          return _Conteudo(primeiro, snap.data!);
        },
      ),
    );
  }
}

class _Conteudo extends StatelessWidget {
  final Perfil a, b;
  const _Conteudo(this.a, this.b);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final c = concordancia(a, b);
    String pos(Perfil p) => p.posicao == null
        ? '—'
        : '${rotuloFaixa(p.posicao!.faixa)} (${porcentagem(p.posicao!.pctEsquerda)} esq.)';
    String part(Perfil p) => p.totalVotacoes == 0 ? '—' : porcentagem(100 * p.participou / p.totalVotacoes);
    return ListView(padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 12), children: [
      Clamp(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: _Pessoa(a)),
            const SizedBox(width: 12),
            Expanded(child: _Pessoa(b)),
          ]),
          const SizedBox(height: 24),
          if (c != null)
            Grupo(
              titulo: 'Votos em comum',
              descricao: 'Contam só as votações em que os dois votaram sim ou não',
              filhos: [
                Linha(
                  titulo: 'Votaram igual',
                  subtitulo: '${c.iguais} de ${c.comuns} votações',
                  valor: porcentagem(100 * c.iguais / c.comuns),
                ),
              ],
            ),
          Grupo(titulo: 'Lado a lado', filhos: [
            _Par('Partido', a.resumo.partido ?? '—', b.resumo.partido ?? '—'),
            _Par('Posição nas votações', pos(a), pos(b)),
            _Par('Participação nas votações', part(a), part(b)),
            _Par(a.salario.teto || b.salario.teto ? 'Salário (ou teto)' : 'Salário', reais(a.salario.atual), reais(b.salario.atual)),
            _Par('Doação do salário', a.doacaoSalario?.titulo ?? 'Não declarada', b.doacaoSalario?.titulo ?? 'Não declarada'),
            _Par('Gastos de gabinete (total)', reais(a.gastos.total), reais(b.gastos.total)),
            _Par('Custo mensal do gabinete', reais(a.custoGabinete?.mensal), reais(b.custoGabinete?.mensal)),
            _Par('Emendas indicadas', reais(a.emendas?.totalEmpenhado), reais(b.emendas?.totalEmpenhado)),
            _Par('Emendas pagas', reais(a.emendas?.totalPago), reais(b.emendas?.totalPago)),
          ]),
          Text(
            'Os valores cobrem todo o período disponível de cada um. Cargos e casas diferentes '
            'têm regras e verbas diferentes.',
            style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    ]);
  }
}

class _Pessoa extends StatelessWidget {
  final Perfil p;
  const _Pessoa(this.p);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Column(children: [
      Avatar(url: p.resumo.foto, nome: p.resumo.nome, tamanho: 64),
      const SizedBox(height: 8),
      Text(p.resumo.nome, textAlign: TextAlign.center, style: tema.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
      Text('${p.resumo.cargo} · ${p.resumo.partidoUf}', textAlign: TextAlign.center, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
    ]);
  }
}

class _Par extends StatelessWidget {
  final String titulo, va, vb;
  const _Par(this.titulo, this.va, this.vb);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final estilo = tema.textTheme.bodyLarge?.copyWith(fontFeatures: const [FontFeature.tabularFigures()]);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(titulo, style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor), textAlign: TextAlign.center),
        const SizedBox(height: 4),
        Row(children: [
          Expanded(child: Text(va, style: estilo, textAlign: TextAlign.center)),
          Expanded(child: Text(vb, style: estilo, textAlign: TextAlign.center)),
        ]),
      ]),
    );
  }
}
