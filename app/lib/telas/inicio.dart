import 'package:flutter/material.dart';

import '../dados/api.dart';
import '../dados/modelos.dart';
import '../formatar.dart';
import '../tema.dart';
import '../widgets/adw.dart';
import 'aparencia.dart';
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

class _InicioState extends State<Inicio> {
  late Future<List<PoliticoResumo>> _lista;
  final _busca = TextEditingController();
  Esfera _esfera = Esfera.todas;
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
      if (_uf != null && p.uf != _uf) return false;
      if (_soEmExercicio && !p.emExercicio) return false;
      if (_soDoaSalario && !p.doaSalario) return false;
      if (termo.isEmpty) return true;
      return semAcento('${p.nome} ${p.partido ?? ''} ${p.uf ?? ''} ${p.cargo} ${p.orgao}'.toLowerCase()).contains(termo);
    }).toList();
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
        Container(width: 1, color: Color.alphaBlend(Theme.of(context).dividerColor, Theme.of(context).scaffoldBackgroundColor)),
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
          PopupMenuButton<VoidCallback>(
            tooltip: 'Menu principal',
            icon: Icon(iconeMenu(Visual.of(context).estilo)),
            onSelected: (acao) => acao(),
            itemBuilder: (_) => [
              PopupMenuItem(
                value: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AparenciaTela())),
                child: const Text('Aparência'),
              ),
              PopupMenuItem(value: () => mostrarSobre(context), child: const Text('Sobre o AraraGov')),
            ],
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
          final filtrados = _filtrar(todos);
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
                      onSelectionChanged: (s) => setState(() => _esfera = s.first),
                    ),
                    const SizedBox(height: 4),
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
                      const SizedBox(width: 8),
                      Expanded(
                        child: Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 4, children: [
                          FilterChip(
                            label: const Text('Doa o salário'),
                            tooltip: 'Quem declara publicamente doar o salário ou parte dele',
                            selected: _soDoaSalario,
                            onSelected: (v) => setState(() => _soDoaSalario = v),
                          ),
                          FilterChip(
                            label: const Text('Em exercício'),
                            selected: _soEmExercicio,
                            onSelected: (v) => setState(() => _soEmExercicio = v),
                          ),
                        ]),
                      ),
                    ]),
                    Text('${filtrados.length} resultados', style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor)),
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
                itemCount: filtrados.length,
                itemBuilder: (context, i) {
                  final p = filtrados[i];
                  return Clamp(
                    child: ListTile(
                      selected: largo && p.id == _selecionado,
                      leading: Avatar(url: p.foto, nome: p.nome),
                      title: Text(p.nome),
                      subtitle: Text('${p.cargo} · ${p.partidoUf}'),
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
