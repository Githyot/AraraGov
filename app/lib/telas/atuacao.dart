import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';

/// Atuação parlamentar e quadro de recursos dos deputados federais, na mesma
/// ordem e com os mesmos nomes da página do deputado no site da Câmara.

Future<void> _abrir(String? url) async {
  if (url != null) await launchUrl(Uri.parse(url));
}

const _mesesExtenso = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

/// Tipos de benefício que o quadro de recursos já mostra (Câmara).
const tiposDoQuadro = {'imovel_funcional', 'auxilio_moradia', 'viagem_missao', 'passaporte_diplomatico'};

/// Ano do quadro de recursos a mostrar: o do filtro, ou o mais recente.
int? anoDoQuadro(Perfil p) {
  final anos = p.quadroRecursos.keys;
  if (p.ano != null) return p.quadroRecursos.containsKey(p.ano) ? p.ano : null;
  return anos.isEmpty ? null : anos.reduce((a, b) => a > b ? a : b);
}

/// Pessoal de gabinete, salário bruto, imóvel funcional, auxílio-moradia,
/// viagens em missão oficial e passaporte diplomático, inclusive quando o
/// deputado não usa o benefício.
class SecaoRecursos extends StatelessWidget {
  final Perfil p;
  const SecaoRecursos(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final ano = anoDoQuadro(p);
    if (ano == null) return const SizedBox.shrink();
    final q = p.quadroRecursos[ano]!;
    final salario = p.salarioPago?.anos[ano];
    final ultimo = salario == null || salario.porMes.isEmpty ? null : salario.porMes.last;
    String pessoal() {
      final n = q.pessoal!;
      final total = '$n ${n == 1 ? 'pessoa' : 'pessoas'} em $ano';
      return q.pessoalAtivo == null ? total : '$total, ${q.pessoalAtivo} no gabinete hoje';
    }

    final abrir = q.fonte == null ? null : () => _abrir(q.fonte);
    return Grupo(
      titulo: 'Recursos em $ano',
      descricao: 'Como a Câmara publica na página do deputado',
      filhos: [
        if (q.pessoal != null) Linha(titulo: 'Pessoal de gabinete', subtitulo: pessoal(), aoTocar: abrir),
        if (ultimo != null)
          Linha(
            titulo: 'Salário mensal bruto',
            subtitulo: 'Pago em ${_mesesExtenso[ultimo.mes - 1]}',
            valor: reais(ultimo.valor),
          ),
        if (q.imovel != null) Linha(titulo: 'Imóvel funcional', subtitulo: q.imovel, aoTocar: abrir),
        if (q.auxilio != null)
          Linha(
            titulo: 'Auxílio-moradia',
            subtitulo: q.auxilioValor != null ? 'Total recebido em $ano' : q.auxilio,
            valor: q.auxilioValor == null ? null : reais(q.auxilioValor, centavos: false),
            aoTocar: abrir,
          ),
        if (q.viagens != null)
          Linha(
            titulo: 'Viagens em missão oficial',
            subtitulo: q.viagens == 0 ? 'Nenhuma em $ano' : null,
            valor: '${q.viagens}',
            aoTocar: abrir,
          ),
        if (q.passaporte != null) Linha(titulo: 'Passaporte diplomático', subtitulo: q.passaporte, aoTocar: abrir),
      ],
    );
  }
}

/// Propostas de autoria, relatorias, emendas, requerimentos, presença no
/// Plenário, discursos, comissões e frentes parlamentares.
class SecaoAtuacao extends StatelessWidget {
  final Perfil p;
  const SecaoAtuacao(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final a = p.atividade;
    if (a == null) return const SizedBox.shrink();
    final tema = Theme.of(context);
    final ano = a.anoMostrado(p.ano);
    final doAno = ano == null ? null : a.anos[ano];
    final prod = doAno?.producao;
    final pres = doAno?.presenca;
    final disc = doAno?.discursos;
    final atuais = a.comissoes.where((c) => c.atual).toList();
    final anteriores = a.comissoes.where((c) => !c.atual).toList();
    return Grupo(
      titulo: ano == null ? 'Atuação parlamentar' : 'Atuação parlamentar em $ano',
      descricao: 'Propostas, relatorias e participação, segundo os dados abertos da Câmara',
      filhos: [
        if (doAno == null && p.ano != null) Linha(titulo: 'Sem atuação registrada em ${p.ano}'),
        if (prod != null) ...[
          Linha(
            titulo: 'Propostas de autoria',
            subtitulo: prod.propostas.isEmpty
                ? 'Projetos de lei, PECs e outras propostas'
                : '${prod.comoPrimeiroAutor} como primeiro autor, ${prod.propostas.length - prod.comoPrimeiroAutor} em coautoria',
            valor: '${prod.propostas.length}',
            aoTocar: prod.propostas.isEmpty
                ? null
                : () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => ListaPropostas(titulo: 'Propostas de ${p.resumo.nome} em $ano', propostas: prod.propostas),
                    )),
          ),
          Linha(
            titulo: 'Relatorias',
            subtitulo: 'Propostas em que deu parecer como relator',
            valor: '${prod.relatorias.length}',
            aoTocar: prod.relatorias.isEmpty
                ? null
                : () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => ListaRelatorias(titulo: 'Relatorias de ${p.resumo.nome} em $ano', relatorias: prod.relatorias),
                    )),
          ),
          Linha(titulo: 'Emendas a propostas', subtitulo: 'Emendas e substitutivos apresentados', valor: '${prod.emendas}'),
          Linha(
            titulo: 'Requerimentos',
            subtitulo: prod.pedidosInformacao == 0
                ? null
                : '${prod.pedidosInformacao} ${prod.pedidosInformacao == 1 ? 'pedido' : 'pedidos'} de informação a ministérios e órgãos',
            valor: '${prod.requerimentos}',
          ),
        ],
        if (pres != null)
          Linha(
            titulo: 'Presença no Plenário',
            subtitulo: 'Presença registrada em ${pres.diasPresente} de ${pres.diasSessao} dias com sessão deliberativa'
                '${pres.periodoParcial ? ', contando só o período em exercício' : ''}. '
                'A Câmara não publica as faltas justificadas nos dados abertos.',
            valor: porcentagem(pres.pct),
          ),
        if (disc != null && disc.total > 0)
          ExpansionTile(
            title: const Text('Discursos'),
            subtitle: Text('${disc.total} em $ano'),
            shape: const Border(),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                child: Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final e in disc.porTipo.entries) Etiqueta('${e.key}: ${e.value}', tema.hintColor),
                ]),
              ),
              for (final d in disc.recentes)
                Linha(
                  titulo: [data(d.data), ?d.tipo].join(' · '),
                  subtitulo: d.trecho,
                  aoTocar: d.link == null ? null : () => _abrir(d.link),
                ),
            ],
          ),
        if (a.comissoes.isNotEmpty)
          ExpansionTile(
            title: const Text('Comissões'),
            subtitle: Text(atuais.isEmpty ? 'Nenhuma hoje' : '${atuais.length} hoje'),
            shape: const Border(),
            children: [
              for (final c in atuais) _LinhaComissao(c),
              if (anteriores.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text('Anteriores', style: tema.textTheme.titleSmall),
                ),
              for (final c in anteriores) _LinhaComissao(c),
            ],
          ),
        if (a.frentes.isNotEmpty)
          ExpansionTile(
            title: const Text('Frentes parlamentares'),
            subtitle: Text(
              '${a.frentes.length} na legislatura atual'
              '${a.frentes.any((f) => f.coordena) ? ', coordena ${a.frentes.where((f) => f.coordena).length}' : ''}',
            ),
            shape: const Border(),
            children: [
              for (final f in a.frentes)
                Linha(titulo: f.titulo, subtitulo: f.coordena ? 'Coordenador' : null),
            ],
          ),
        if (p.ano != null && (a.comissoes.isNotEmpty || a.frentes.isNotEmpty))
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: Text(
              'Comissões e frentes são de toda a legislatura, não só de ${p.ano}.',
              style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
            ),
          ),
      ],
    );
  }
}

class _LinhaComissao extends StatelessWidget {
  final Comissao c;
  const _LinhaComissao(this.c);

  @override
  Widget build(BuildContext context) {
    final periodo = c.atual
        ? (c.inicio == null ? null : 'desde ${data(c.inicio)}')
        : '${c.inicio == null ? '' : '${data(c.inicio)} a '}${data(c.fim)}';
    return Linha(titulo: c.nome, subtitulo: [?c.cargo, ?periodo].join(' · '));
  }
}

class ListaPropostas extends StatefulWidget {
  final String titulo;
  final List<Proposta> propostas;
  const ListaPropostas({super.key, required this.titulo, required this.propostas});

  @override
  State<ListaPropostas> createState() => _ListaPropostasState();
}

class _ListaPropostasState extends State<ListaPropostas> {
  bool soPrimeiro = false;

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final lista = soPrimeiro ? widget.propostas.where((p) => p.primeiroAutor).toList() : widget.propostas;
    return Scaffold(
      appBar: AppBar(title: Text(widget.titulo)),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: Adw.espaco, vertical: 12),
        children: [
          Clamp(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: SegmentedButton<bool>(
                  segments: [
                    ButtonSegment(value: false, label: Text('Todas (${widget.propostas.length})')),
                    ButtonSegment(
                      value: true,
                      label: Text('Primeiro autor (${widget.propostas.where((p) => p.primeiroAutor).length})'),
                    ),
                  ],
                  selected: {soPrimeiro},
                  onSelectionChanged: (v) => setState(() => soPrimeiro = v.first),
                ),
              ),
              Grupo(filhos: [
                for (final p in lista)
                  ListTile(
                    title: Text(p.rotulo),
                    subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(p.ementa),
                      const SizedBox(height: 4),
                      Text(
                        [
                          if (p.data != null) 'Apresentada em ${data(p.data)}',
                          if (!p.primeiroAutor) 'coautoria',
                          ?p.situacao,
                        ].join(' · '),
                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                      ),
                    ]),
                    onTap: () => _abrir(p.link),
                  ),
              ]),
            ]),
          ),
        ],
      ),
    );
  }
}

class ListaRelatorias extends StatelessWidget {
  final String titulo;
  final List<Relatoria> relatorias;
  const ListaRelatorias({super.key, required this.titulo, required this.relatorias});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(titulo)),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: Adw.espaco, vertical: 12),
        children: [
          Clamp(
            child: Grupo(
              descricao: 'O parecer é o voto do relator sobre a proposta. A situação é a atual da proposta.',
              titulo: '${relatorias.length} propostas relatadas',
              filhos: [
                for (final r in relatorias)
                  ListTile(
                    title: Text(r.rotulo),
                    subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(r.ementa),
                      const SizedBox(height: 4),
                      Text(
                        [
                          if (r.data != null) 'Parecer de ${data(r.data)}',
                          if (r.conclusao != null) r.conclusao!,
                          ?r.situacao,
                        ].join(' · '),
                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                      ),
                    ]),
                    onTap: () => _abrir(r.link),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
