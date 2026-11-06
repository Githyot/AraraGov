import 'package:flutter/material.dart';

import '../tema.dart';
import 'adw.dart';

/// Rótulo e cor neutros para cada tipo de voto.
const votoRotulo = {
  'sim': 'Sim',
  'nao': 'Não',
  'abstencao': 'Abstenção',
  'obstrucao': 'Obstrução',
  'ausente': 'Ausente',
  'licenca': 'Licença',
  'missao': 'Missão oficial',
  'presidente': 'Presidindo',
  'presente_sem_voto': 'Presente, sem voto',
  'outro': 'Outro',
};

/// Sim e Não usam azul e roxo de propósito: verde e vermelho sugerem
/// "certo" e "errado", e o app não julga votos. Os demais tipos ficam em
/// cinza, porque não são nem a favor nem contra.
Color votoCor(String voto) => switch (voto) {
      'sim' => Adw.azul,
      'nao' => Adw.roxo,
      _ => Colors.grey,
    };

class EtiquetaVoto extends StatelessWidget {
  final String voto;
  const EtiquetaVoto(this.voto, {super.key});
  @override
  Widget build(BuildContext context) => Etiqueta(votoRotulo[voto] ?? voto, votoCor(voto));
}
