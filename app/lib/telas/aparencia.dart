import 'package:flutter/material.dart';

import '../tema.dart';
import '../widgets/adw.dart';

/// Aparência: estilo visual (GNOME, Android, Apple, Windows) e modo
/// claro/escuro. A troca vale na hora e fica salva.
class AparenciaTela extends StatelessWidget {
  const AparenciaTela({super.key});

  @override
  Widget build(BuildContext context) {
    final a = AparenciaEscopo.of(context);
    final v = Visual.of(context);
    final marca = Icon(Icons.check, color: Theme.of(context).colorScheme.primary);
    final doSistema = EstiloVisual.automatico.resolver().rotulo;
    return Scaffold(
      appBar: AppBar(title: const Text('Aparência')),
      body: ListView(
        padding: const EdgeInsets.all(Esp.margem),
        children: [
          Clamp(
            largura: 560,
            child: Column(
              children: [
                Grupo(
                  titulo: 'Estilo',
                  descricao: 'O jeito dos botões, listas e cantos. As cores dos dados não mudam.',
                  filhos: [
                    for (final e in EstiloVisual.values)
                      Linha(
                        titulo: e.rotulo,
                        subtitulo: e == EstiloVisual.automatico
                            ? 'Segue o sistema do aparelho ($doSistema)'
                            : e.descricao,
                        sufixo: a.estilo == e ? marca : const SizedBox(width: Tam.icone),
                        aoTocar: () => a.estilo = e,
                      ),
                  ],
                ),
                Grupo(
                  titulo: 'Modo',
                  filhos: [
                    for (final (m, rotulo) in const [
                      (ThemeMode.system, 'Igual ao sistema'),
                      (ThemeMode.light, 'Claro'),
                      (ThemeMode.dark, 'Escuro'),
                    ])
                      Linha(titulo: rotulo, sufixo: a.modo == m ? marca : const SizedBox(width: Tam.icone), aoTocar: () => a.modo = m),
                  ],
                ),
                Text(
                  'Estilo atual: ${v.estilo.rotulo}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: v.corSecundaria),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Ícone do menu principal no jeito de cada sistema.
IconData iconeMenu(EstiloVisual e) => switch (e) {
  EstiloVisual.android => Icons.more_vert,
  EstiloVisual.apple => Icons.more_horiz,
  _ => Icons.menu,
};
