import 'package:flutter/material.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import 'municipios.dart';
import 'perfil.dart';
import 'sobre.dart';

/// Tela inicial: busca de políticos. Em telas largas mostra lista e perfil
/// lado a lado (AdwNavigationSplitView); em telas estreitas, um de cada vez.
class Inicio extends StatefulWidget {
  final Api api;
  const Inicio({super.key, required this.api});

  @override
  State<Inicio> createState() => _InicioState();
}

enum Esfera { todas, federal, estadual }

/// Ordem dos cargos na lista e nos filtros: primeiro o Executivo, depois a
/// casa mais alta. Cargo fora da lista vai para o fim.
const _ordemCargos = ['Governador', 'Vice-governador', 'Senador', 'Deputado Federal', 'Deputado estadual'];

const _pluralCargos = {
  'Governador': 'Governadores',
  'Vice-governador': 'Vice-governadores',
  'Senador': 'Senadores',
  'Deputado Federal': 'Deputados federais',
  'Deputado estadual': 'Deputados estaduais',
};

int _posicaoCargo(String cargo) {
  final i = _ordemCargos.indexOf(cargo);
  return i < 0 ? _ordemCargos.length : i;
}

/// "Deputado Federal" → "Deputado federal": as fontes não seguem o mesmo padrão.
String _rotuloCargo(String cargo) => cargo.isEmpty ? cargo : cargo[0] + cargo.substring(1).toLowerCase();

String _pluralCargo(String cargo) => _pluralCargos[cargo] ?? _rotuloCargo(cargo);

/// No filtro a esfera já foi escolhida, então "Deputados" basta e cabe no celular.
String _pluralCurto(String cargo) => cargo.startsWith('Deputado') ? 'Deputados' : _pluralCargo(cargo);

class _InicioState extends State<Inicio> {
  late Future<List<PoliticoResumo>> _lista;
  final _busca = TextEditingController();
  Esfera _esfera = Esfera.todas;
  String? _cargo;
  String? _uf;
  bool _soEmExercicio = true;
  bool _soDoaSalario = false;
  String? _selecionado;

  @override
  void initState() {
    super.initState();
    _carregar();
    _busca.addListener(() => setState(() {}));
  }

  void _carregar() => _lista = widget.api.politicos();

  List<PoliticoResumo> _filtrar(List<PoliticoResumo> todos) {
    final termo = semAcento(_busca.text.trim().toLowerCase());
    return todos.where((p) {
      if (_esfera != Esfera.todas && p.esfera != _esfera.name) return false;
      if (_cargo != null && p.cargo != _cargo) return false;
      if (_uf != null && p.uf != _uf) return false;
      if (_soEmExercicio && !p.emExercicio) return false;
      if (_soDoaSalario && !p.doaSalario) return false;
      if (termo.isEmpty) return true;
      return semAcento('${p.nome} ${p.partido ?? ''} ${p.uf ?? ''} ${p.cargo} ${p.orgao}'.toLowerCase()).contains(termo);
    }).toList()
      ..sort((a, b) {
        final c = _posicaoCargo(a.cargo).compareTo(_posicaoCargo(b.cargo));
        return c != 0 ? c : semAcento(a.nome.toLowerCase()).compareTo(semAcento(b.nome.toLowerCase()));
      });
  }

  /// Cargos que existem na esfera escolhida, para o segundo filtro.
  List<String> _cargosDaEsfera(List<PoliticoResumo> todos) {
    if (_esfera == Esfera.todas) return const [];
    final cargos = {for (final p in todos) if (p.esfera == _esfera.name) p.cargo}.toList()
      ..sort((a, b) => _posicaoCargo(a).compareTo(_posicaoCargo(b)));
    return cargos;
  }

  /// Lista com um cabeçalho antes de cada cargo, quando há mais de um.
  List<Object> _comSecoes(List<PoliticoResumo> lista) {
    final cargos = {for (final p in lista) p.cargo};
    if (cargos.length < 2) return lista;
    final contagem = <String, int>{};
    for (final p in lista) {
      contagem[p.cargo] = (contagem[p.cargo] ?? 0) + 1;
    }
    final itens = <Object>[];
    String? atual;
    for (final p in lista) {
      if (p.cargo != atual) {
        atual = p.cargo;
        itens.add((cargo: atual, total: contagem[atual]!));
      }
      itens.add(p);
    }
    return itens;
  }

  void _abrir(PoliticoResumo p, bool largo) {
    if (largo) {
      setState(() => _selecionado = p.id);
    } else {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => PerfilTela(api: widget.api, id: p.id, resumo: p)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final largo = c.maxWidth >= 900;
      final lista = _painelLista(largo);
      if (!largo) return lista;
      return Row(children: [
        SizedBox(width: 380, child: lista),
        VerticalDivider(width: 1, color: Theme.of(context).dividerTheme.color),
        Expanded(
          child: _selecionado == null
              ? const Scaffold(
                  body: StatusPage(
                    mascote: 'happy',
                    titulo: 'Escolha um político',
                    descricao: 'Veja salário, gastos, votações e gabinete de cada deputado e senador.',
                  ),
                )
              : PerfilTela(key: ValueKey(_selecionado), api: widget.api, id: _selecionado!, embutido: true),
        ),
      ]);
    });
  }

  Widget _painelLista(bool largo) {
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('AraraGov'),
        actions: [
          IconButton(
            tooltip: 'Municípios',
            icon: const Icon(Icons.location_city_outlined),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MunicipiosTela(api: widget.api))),
          ),
          IconButton(
            tooltip: 'Sobre',
            icon: const Icon(Icons.info_outline),
            onPressed: () => mostrarSobre(context),
          ),
        ],
      ),
      body: FutureBuilder<List<PoliticoResumo>>(
        future: _lista,
        builder: (context, snap) {
          if (snap.hasError) {
            return StatusPage(
              mascote: 'sad',
              titulo: 'Não foi possível carregar',
              descricao: 'Verifique sua conexão e tente de novo.\n${snap.error}',
              acao: FilledButton(onPressed: () => setState(_carregar), child: const Text('Tentar de novo')),
            );
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final todos = snap.data!;
          final ufs = {for (final p in todos) if (p.uf != null) p.uf!}.toList()..sort();
          final cargos = _cargosDaEsfera(todos);
          if (_cargo != null && !cargos.contains(_cargo)) _cargo = null;
          final filtrados = _filtrar(todos);
          final itens = _comSecoes(filtrados);
          return CustomScrollView(slivers: [
            SliverToBoxAdapter(
              child: Clamp(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(Adw.espaco, Adw.espaco, Adw.espaco, 4),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    TextField(
                      controller: _busca,
                      decoration: InputDecoration(
                        hintText: 'Buscar por nome, partido, cargo ou estado',
                        prefixIcon: const Icon(Icons.search, size: 20),
                        suffixIcon: _busca.text.isEmpty
                            ? null
                            : IconButton(icon: const Icon(Icons.clear, size: 18), onPressed: _busca.clear),
                      ),
                    ),
                    const SizedBox(height: 10),
                    SegmentedButton<Esfera>(
                      showSelectedIcon: false,
                      segments: const [
                        ButtonSegment(value: Esfera.todas, label: Text('Todos')),
                        ButtonSegment(value: Esfera.federal, label: Text('Federal')),
                        ButtonSegment(value: Esfera.estadual, label: Text('Estadual')),
                      ],
                      selected: {_esfera},
                      onSelectionChanged: (s) => setState(() {
                        _esfera = s.first;
                        _cargo = null;
                      }),
                    ),
                    if (cargos.length > 1) ...[
                      const SizedBox(height: 8),
                      SegmentedButton<String>(
                        showSelectedIcon: false,
                        segments: [
                          const ButtonSegment(value: '', label: Text('Todos')),
                          for (final c in cargos) ButtonSegment(value: c, label: Text(_pluralCurto(c))),
                        ],
                        selected: {_cargo ?? ''},
                        onSelectionChanged: (s) => setState(() => _cargo = s.first.isEmpty ? null : s.first),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      FilterChip(
                        label: const Text('Em exercício'),
                        selected: _soEmExercicio,
                        onSelected: (v) => setState(() => _soEmExercicio = v),
                      ),
                      FilterChip(
                        label: const Text('Doa o salário'),
                        tooltip: 'Quem declara publicamente doar o salário ou parte dele',
                        selected: _soDoaSalario,
                        onSelected: (v) => setState(() => _soDoaSalario = v),
                      ),
                    ]),
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
                      Text(
                        filtrados.length == 1 ? '1 resultado' : '${filtrados.length} resultados',
                        style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                      ),
                    ]),
                  ]),
                ),
              ),
            ),
            if (filtrados.isEmpty)
              const SliverFillRemaining(
                hasScrollBody: false,
                child: StatusPage(mascote: 'think', titulo: 'Ninguém encontrado', descricao: 'Tente outro nome ou tire os filtros.'),
              )
            else
              SliverList.builder(
                itemCount: itens.length,
                itemBuilder: (context, i) {
                  final item = itens[i];
                  if (item is ({String cargo, int total})) {
                    return Clamp(
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.fromLTRB(Adw.espaco + 4, Adw.espaco, Adw.espaco, 4),
                        child: Text(
                          '${_pluralCargo(item.cargo)} · ${item.total}',
                          style: tema.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ),
                    );
                  }
                  final p = item as PoliticoResumo;
                  return Clamp(
                    child: ListTile(
                      selected: largo && p.id == _selecionado,
                      leading: Avatar(url: p.foto, nome: p.nome),
                      title: Text(p.nome),
                      subtitle: Text([_rotuloCargo(p.cargo), if (p.partidoUf.isNotEmpty) p.partidoUf].join(' · ')),
                      trailing: largo ? null : const Icon(Icons.chevron_right),
                      onTap: () => _abrir(p, largo),
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
