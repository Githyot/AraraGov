import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/api.dart';
import '../dados/contas_municipio.dart';
import '../dados/md.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import '../widgets/lai.dart';

part 'municipio_dinheiro.dart';

/// Busca de municípios (lista do `municipios/indice.md`).
class MunicipiosTela extends StatefulWidget {
  final Api api;
  const MunicipiosTela({super.key, required this.api});

  @override
  State<MunicipiosTela> createState() => _MunicipiosTelaState();
}

class _MunicipiosTelaState extends State<MunicipiosTela> {
  late Future<DocumentoMd?> _indice;
  final _busca = TextEditingController();
  String? _uf;

  @override
  void initState() {
    super.initState();
    _indice = widget.api.md('municipios/indice.md');
    _busca.addListener(() => setState(() {}));
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Municípios')),
      body: FutureBuilder<DocumentoMd?>(
        future: _indice,
        builder: (context, snap) {
          if (snap.hasError) {
            return StatusPage(
              mascote: 'sad',
              titulo: 'Não foi possível carregar',
              descricao: 'Verifique sua conexão e tente de novo.\n${snap.error}',
              acao: FilledButton(
                onPressed: () => setState(() => _indice = widget.api.md('municipios/indice.md')),
                child: const Text('Tentar de novo'),
              ),
            );
          }
          if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          final todos = snap.data?.tabela('municipios') ?? const [];
          if (todos.isEmpty) {
            return const StatusPage(
              mascote: 'think',
              titulo: 'Não há dados',
              descricao: 'A lista de municípios ainda não foi publicada pela coleta do AraraGov.',
            );
          }
          final ufs = {for (final m in todos) m['uf'] ?? ''}.where((u) => u.isNotEmpty).toList()..sort();
          final termo = semAcento(_busca.text.trim().toLowerCase());
          final lista = todos.where((m) {
            if (_uf != null && m['uf'] != _uf) return false;
            return termo.isEmpty || semAcento((m['municipio'] ?? '').toLowerCase()).contains(termo);
          }).toList();
          return CustomScrollView(slivers: [
            SliverToBoxAdapter(
              child: Clamp(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(Adw.espaco, Adw.espaco, Adw.espaco, 4),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    TextField(
                      controller: _busca,
                      decoration: const InputDecoration(hintText: 'Buscar município', prefixIcon: Icon(Icons.search, size: 20)),
                    ),
                    Row(children: [
                      DropdownButton<String?>(
                        value: _uf,
                        underline: const SizedBox(),
                        hint: const Text('Todos os estados'),
                        items: [
                          const DropdownMenuItem(value: null, child: Text('Todos os estados')),
                          for (final uf in ufs) DropdownMenuItem(value: uf, child: Text(uf)),
                        ],
                        onChanged: (v) => setState(() => _uf = v),
                      ),
                      const Spacer(),
                      Text('${lista.length} municípios', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
                    ]),
                  ]),
                ),
              ),
            ),
            SliverList.builder(
              itemCount: lista.length,
              itemBuilder: (context, i) {
                final m = lista[i];
                final prefeito = m['prefeito'];
                return Clamp(
                  child: ListTile(
                    title: Text('${m['municipio']} (${m['uf']})'),
                    subtitle: Text(prefeito == null ? 'Prefeito: não há dados' : 'Prefeito: $prefeito (${m['partido'] ?? '—'})'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => MunicipioTela(api: widget.api, ibge: m['ibge']!, uf: m['uf']!, nome: m['municipio']!),
                    )),
                  ),
                );
              },
            ),
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ]);
        },
      ),
    );
  }
}

/// Um município: quem governa, dinheiro, obras, fornecedores e emendas.
class MunicipioTela extends StatelessWidget {
  final Api api;
  final String ibge, uf, nome;
  const MunicipioTela({super.key, required this.api, required this.ibge, required this.uf, required this.nome});

  String get pasta => 'municipios/${uf.toLowerCase()}/$ibge';

  @override
  Widget build(BuildContext context) {
    const abas = ['Quem governa', 'Dinheiro', 'Obras', 'Fornecedores', 'Emendas'];
    return DefaultTabController(
      length: abas.length,
      child: Scaffold(
        appBar: AppBar(
          title: Text('$nome ($uf)'),
          actions: [
            IconButton(
              tooltip: 'Pedir documentos à prefeitura (LAI)',
              icon: const Icon(Icons.mail_outline),
              onPressed: () => mostrarPedidoLai(
                  context, PedidoLai(municipio: nome, uf: uf, assunto: 'despesas e contratos da prefeitura')),
            ),
          ],
          bottom: TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [for (final a in abas) Tab(text: a)]),
        ),
        body: TabBarView(children: [
          _Governo(api: api, pasta: pasta),
          _Dinheiro(api: api, pasta: pasta, uf: uf),
          _Obras(api: api, pasta: pasta, uf: uf, nome: nome),
          _Fornecedores(api: api, pasta: pasta, uf: uf, nome: nome),
          _Emendas(api: api, pasta: pasta),
        ]),
      ),
    );
  }
}

// --- peças comuns -----------------------------------------------------------------

double _n(String? v) => numeroMd(v) ?? 0;

String _reais(String? v) => v == null ? 'Não há dados' : reais(numeroMd(v));

/// Rolagem com largura limitada, padrão de todas as abas.
class _Pagina extends StatelessWidget {
  final List<Widget> filhos;
  const _Pagina(this.filhos);

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(Adw.espaco),
        children: [Clamp(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: filhos))],
      );
}

/// Carrega um ou mais .md e monta a aba; trata espera e erro.
class _Carregar extends StatelessWidget {
  final Future<List<DocumentoMd?>> futuro;
  final Widget Function(List<DocumentoMd?>) montar;
  const _Carregar({required this.futuro, required this.montar});

  @override
  Widget build(BuildContext context) => FutureBuilder<List<DocumentoMd?>>(
        future: futuro,
        builder: (context, snap) {
          if (snap.hasError) {
            return StatusPage(mascote: 'sad', titulo: 'Não foi possível carregar', descricao: '${snap.error}');
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          return montar(snap.data!);
        },
      );
}

/// "Não há dados", com quem deveria ter publicado (tabela `sem-dados`) ou,
/// sem ela, o motivo informado pelo app.
class _SemDados extends StatelessWidget {
  final List<Map<String, String?>> linhas;
  final String? motivo;
  const _SemDados({this.linhas = const [], this.motivo});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    if (linhas.isEmpty && motivo == null) return const SizedBox.shrink();
    return Grupo(
      titulo: 'Não há dados',
      filhos: [
        if (linhas.isEmpty)
          ListTile(leading: const Icon(Icons.info_outline), title: Text(motivo!))
        else
          for (final s in linhas)
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: Text(s['motivo'] ?? 'Sem dados'),
              subtitle: Text([
                if (s['responsavel'] != null) 'Responsável: ${s['responsavel']} (esfera ${s['esfera'] ?? '—'})',
                if (s['obrigacao'] != null) s['obrigacao']!,
                if (s['consultado_em'] != null) 'Consultado em ${data(s['consultado_em'])}',
              ].join('\n'), style: tema.textTheme.bodySmall),
              onTap: s['fonte_consultada'] == null ? null : () => _abrir(s['fonte_consultada']!),
            ),
      ],
    );
  }
}

Future<void> _abrir(String url) async => launchUrl(Uri.parse(url));

/// Tribunais de contas cujos pagamentos, um a um, já são lidos.
const _tribunais = {'SP': 'TCE-SP', 'CE': 'TCE-CE', 'PB': 'TCE-PB', 'PE': 'TCE-PE'};

String _semTce(String uf) => _tribunais.containsKey(uf)
    ? 'Ainda não coletado para este município.'
    : 'Nenhum contrato desta prefeitura no PNCP nos anos coletados. Pagamentos um a um só existem, '
        'por enquanto, para ${_tribunais.keys.join(', ')} (Tribunais de Contas).';

/// Anos com arquivo publicado, do mais recente ao mais antigo.
Future<Map<int, DocumentoMd>> _porAno(Api api, String pasta, String sufixo) async {
  final ultimo = DateTime.now().year;
  final anos = [for (var a = ultimo; a >= 2019; a--) a];
  final docs = await Future.wait([for (final a in anos) api.md('$pasta/$a$sufixo.md').catchError((_) => null)]);
  return {for (var i = 0; i < anos.length; i++) if (docs[i] != null) anos[i]: docs[i]!};
}

/// Escolha do ano, quando há mais de um.
class _Anos extends StatelessWidget {
  final List<int> anos;
  final int atual;
  final ValueChanged<int> aoMudar;
  const _Anos({required this.anos, required this.atual, required this.aoMudar});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Wrap(spacing: 8, runSpacing: 4, children: [
          for (final a in anos)
            ChoiceChip(label: Text('$a'), selected: a == atual, onSelected: (_) => aoMudar(a)),
        ]),
      );
}

Color _corComparacao(String? c) {
  if (c == null) return Colors.grey;
  if (c.contains('acima da faixa')) return Adw.amarelo;
  if (c.startsWith('Dentro')) return Adw.verde;
  if (c.startsWith('Abaixo')) return Adw.azul;
  return Colors.grey;
}

// --- abas -------------------------------------------------------------------------

class _Governo extends StatelessWidget {
  final Api api;
  final String pasta;
  const _Governo({required this.api, required this.pasta});

  @override
  Widget build(BuildContext context) => _Carregar(
        futuro: Future.wait([api.md('$pasta/resumo.md')]),
        montar: (docs) {
          final doc = docs[0];
          final mandatos = doc?.tabela('mandatos') ?? const [];
          if (mandatos.isEmpty) {
            return _Pagina([
              _SemDados(linhas: doc?.tabela('sem-dados') ?? const [], motivo: 'O resumo deste município ainda não foi coletado.'),
            ]);
          }
          final eleicoes = {for (final m in mandatos) m['eleicao'] ?? ''}.toList()..sort((a, b) => b.compareTo(a));
          return _Pagina([
            for (final e in eleicoes) ...[
              Grupo(
                titulo: () {
                  final m = mandatos.firstWhere((m) => m['eleicao'] == e);
                  return 'Mandato ${m['inicio']}–${m['fim']} (eleição de $e)';
                }(),
                filhos: [
                  for (final m in mandatos.where((m) => m['eleicao'] == e && m['cargo'] != 'Vereador'))
                    Linha(titulo: m['nome'] ?? '—', subtitulo: '${m['cargo']} · ${m['partido'] ?? '—'}'),
                  ExpansionTile(
                    title: Text('Vereadores (${mandatos.where((m) => m['eleicao'] == e && m['cargo'] == 'Vereador').length})'),
                    children: [
                      for (final m in mandatos.where((m) => m['eleicao'] == e && m['cargo'] == 'Vereador'))
                        Linha(titulo: m['nome'] ?? '—', subtitulo: m['partido']),
                    ],
                  ),
                ],
              ),
            ],
            _SemDados(linhas: doc?.tabela('sem-dados') ?? const []),
            const _Fonte('Tribunal Superior Eleitoral (candidaturas eleitas)'),
          ]);
        },
      );
}

class _Fonte extends StatelessWidget {
  final String texto;
  const _Fonte(this.texto);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 0, 4, 24),
      child: Text('Fonte: $texto', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
    );
  }
}

class _Obras extends StatefulWidget {
  final Api api;
  final String pasta, uf, nome;
  const _Obras({required this.api, required this.pasta, required this.uf, required this.nome});

  @override
  State<_Obras> createState() => _ObrasState();
}

class _ObrasState extends State<_Obras> {
  late final Future<List<Map<int, DocumentoMd>>> _dados =
      Future.wait([_porAno(widget.api, widget.pasta, '-contratos'), _porAno(widget.api, widget.pasta, '-pagamentos')]);
  int? _ano;

  @override
  Widget build(BuildContext context) => FutureBuilder<List<Map<int, DocumentoMd>>>(
        future: _dados,
        builder: (context, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final contratos = snap.data![0];
          final pagamentos = snap.data![1];
          final anos = {...contratos.keys, ...pagamentos.keys}.toList()..sort((a, b) => b.compareTo(a));
          if (anos.isEmpty) return _Pagina([_SemDados(motivo: 'Obras e contratos: ${_semTce(widget.uf)}')]);
          final ano = _ano ?? anos.first;
          final obras = contratos[ano]?.tabela('obras') ?? const [];
          final pagas = pagamentos[ano]?.tabela('obras') ?? const [];
          final diretas = contratos[ano]?.tabela('contratacoes-diretas') ?? const [];
          return _Pagina([
            if (anos.length > 1) _Anos(anos: anos, atual: ano, aoMudar: (a) => setState(() => _ano = a)),
            Grupo(
              titulo: 'Contratos de obras e o custo de referência',
              descricao: 'Acima da faixa não quer dizer irregular: terreno, distância e especificação mudam o preço. É um ponto para perguntar.',
              filhos: obras.isEmpty
                  ? [const ListTile(title: Text('Não há contratos de obra identificados neste ano.'))]
                  : [
                      for (final o in obras)
                        ListTile(
                          title: Text(o['objeto'] ?? '—'),
                          subtitle: Text([
                            '${o['empresa'] ?? '—'} · ${_reais(o['valor'])}',
                            if (o['valor_unitario'] != null && o['unidade'] != null)
                              '${_reais(o['valor_unitario'])} por ${o['unidade']}'
                                  '${o['ref_minimo'] == null ? '' : ' (faixa ${_reais(o['ref_minimo'])} a ${_reais(o['ref_maximo'])}, nível ${o['nivel']})'}',
                            if (o['aviso'] != null) o['aviso']!,
                          ].join('\n')),
                          trailing: Etiqueta(_rotulo(o['comparacao']), _corComparacao(o['comparacao'])),
                          isThreeLine: true,
                          onTap: () => mostrarPedidoLai(
                            context,
                            PedidoLai(
                              municipio: widget.nome,
                              uf: widget.uf,
                              assunto: 'o contrato de obra "${o['objeto'] ?? '—'}" (${o['empresa'] ?? 'empresa não informada'}, $ano)',
                              itens: const [
                                'Contrato, aditivos e projeto básico',
                                'Planilha orçamentária e medições',
                                'Notas de empenho, liquidação e pagamento, com as notas fiscais',
                              ],
                            ),
                          ),
                        ),
                    ],
            ),
            if (pagas.isNotEmpty)
              Grupo(
                titulo: 'Obras pagas no ano',
                filhos: [
                  for (final o in pagas)
                    Linha(titulo: o['acao'] ?? o['historico'] ?? '—', subtitulo: o['favorecido'], valor: _reais(o['pago'])),
                ],
              ),
            if (diretas.isNotEmpty)
              Grupo(
                titulo: 'Mesma empresa com várias contratações diretas',
                descricao: 'Contratações sem licitação permitidas por lei, somadas no ano.',
                filhos: [
                  for (final d in diretas)
                    Linha(titulo: d['empresa'] ?? '—', subtitulo: '${d['contratacoes']} contratações · ${d['cnpj']}', valor: _reais(d['valor'])),
                ],
              ),
            _SemDados(linhas: contratos[ano]?.tabela('sem-dados') ?? const []),
            _Fonte(switch (widget.uf) {
              'SP' => 'TCE-SP (contratos e despesas)',
              'RJ' => 'TCE-RJ (contratos dos municípios) ou PNCP, na capital',
              _ => 'PNCP (Portal Nacional de Contratações Públicas)',
            }),
          ]);
        },
      );

  String _rotulo(String? c) {
    if (c == null) return 'Sem comparação';
    if (c.contains('acima da faixa')) return '${c.split(' acima').first.replaceAll('.', ',')} acima';
    if (c.startsWith('Dentro')) return 'Na faixa';
    if (c.startsWith('Abaixo')) return 'Abaixo';
    return 'Sem comparação';
  }
}

class _Fornecedores extends StatelessWidget {
  final Api api;
  final String pasta, uf, nome;
  const _Fornecedores({required this.api, required this.pasta, required this.uf, required this.nome});

  @override
  Widget build(BuildContext context) => _Carregar(
        futuro: Future.wait([api.md('$pasta/fornecedores.md')]),
        montar: (docs) {
          final doc = docs[0];
          if (doc == null) return _Pagina([_SemDados(motivo: 'Fornecedores: ${_semTce(uf)}')]);
          final tema = Theme.of(context);
          return _Pagina([
            Grupo(
              titulo: 'Empresas que receberam ou foram contratadas',
              descricao: 'Os indícios só apontam fatos com fonte pública. Nenhum é prova de irregularidade.',
              filhos: [
                for (final f in doc.tabela('fornecedores'))
                  ListTile(
                    title: Text(f['empresa'] ?? '—'),
                    subtitle: Text([
                      '${f['cnpj']} · pago ${_reais(f['pago'])} · ${f['contratos'] ?? 0} contratos (${_reais(f['valor_contratos'])})',
                      if (f['indicios'] != null) f['indicios']!,
                    ].join('\n')),
                    leading: f['indicios'] == null ? null : const Icon(Icons.flag_outlined, color: Adw.amarelo),
                    onTap: () => mostrarPedidoLai(
                      context,
                      PedidoLai(
                        municipio: nome,
                        uf: uf,
                        assunto: 'os pagamentos e contratos com ${f['empresa'] ?? 'a empresa'} (CNPJ ${f['cnpj'] ?? '—'})',
                        itens: const [
                          'Contratos e aditivos com a empresa',
                          'Notas de empenho, liquidação e pagamento, com as notas fiscais',
                          'Comprovação da entrega (medições, termos de recebimento)',
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            if (doc.tabela('sancoes').isNotEmpty)
              Grupo(
                titulo: 'Sanções registradas (CEIS e CNEP)',
                descricao: 'A sanção pode ter sido aplicada por outro órgão e valer só para ele: veja a abrangência.',
                filhos: [
                  for (final s in doc.tabela('sancoes'))
                    ListTile(
                      title: Text('${s['empresa']} · ${s['cadastro']}'),
                      subtitle: Text('${s['sancao']}\n${s['orgao'] ?? '—'} · ${data(s['inicio'])} a ${data(s['fim'])}\n${s['abrangencia'] ?? ''}',
                          style: tema.textTheme.bodySmall),
                      isThreeLine: true,
                      onTap: s['fonte'] == null ? null : () => _abrir(s['fonte']!),
                    ),
                ],
              ),
            if (doc.tabela('campanha').isNotEmpty)
              Grupo(
                titulo: 'Também serviram a campanhas no município',
                descricao: 'Serviços declarados pelos candidatos ao TSE. Não é proibido; serve para conferir.',
                filhos: [
                  for (final c in doc.tabela('campanha'))
                    Linha(
                      titulo: c['empresa'] ?? '—',
                      subtitulo: '${c['candidato']} (${c['cargo']}, ${c['partido']}) · ${c['eleicao']} · eleito: ${c['eleito']}',
                      valor: _reais(c['valor']),
                    ),
                ],
              ),
            _SemDados(linhas: doc.tabela('sem-dados')),
            _Fonte('${_tribunais[uf] ?? 'PNCP'}, CGU (CEIS e CNEP) e TSE (prestação de contas)'),
          ]);
        },
      );
}

class _Emendas extends StatelessWidget {
  final Api api;
  final String pasta;
  const _Emendas({required this.api, required this.pasta});

  @override
  Widget build(BuildContext context) => _Carregar(
        futuro: Future.wait([api.md('$pasta/emendas.md')]),
        montar: (docs) {
          final doc = docs[0];
          if (doc == null) {
            return const _Pagina([_SemDados(motivo: 'Nenhuma emenda federal paga a favorecidos deste município nos anos coletados.')]);
          }
          return _Pagina([
            Grupo(
              titulo: 'Emendas recebidas por ano',
              filhos: [
                for (final r in doc.tabela('resumo'))
                  Linha(
                    titulo: '${r['ano']}',
                    subtitulo: '${r['emendas']} emendas de ${r['autores']} autores · governo municipal ${_reais(r['para_prefeitura'])} · outros ${_reais(r['para_outros'])}',
                    valor: _reais(r['valor']),
                  ),
              ],
            ),
            Grupo(
              titulo: 'Quem mandou',
              filhos: [
                for (final a in doc.tabela('autores').take(30))
                  Linha(titulo: a['autor'] ?? 'Autor não informado', subtitulo: '${a['tipo'] ?? '—'} · ${a['emendas']} emendas', valor: _reais(a['valor'])),
              ],
            ),
            Grupo(
              titulo: 'Quem recebeu',
              descricao: 'Receber emenda não é irregular; a lista mostra o caminho do dinheiro.',
              filhos: [
                for (final r in doc.tabela('recebido').take(100))
                  Linha(
                    titulo: r['favorecido'] ?? '—',
                    subtitulo: '${r['ano']} · ${r['autor'] ?? '—'} · ${r['funcao'] ?? '—'}${r['cnpj'] == null ? '' : ' · ${r['cnpj']}'}',
                    valor: _reais(r['valor']),
                  ),
              ],
            ),
            _SemDados(linhas: doc.tabela('sem-dados')),
            const _Fonte('Portal da Transparência (CGU), emendas parlamentares'),
          ]);
        },
      );
}
