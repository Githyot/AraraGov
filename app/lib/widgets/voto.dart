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

Color votoCor(String voto) => switch (voto) {
      'sim' => Adw.verde,
      'nao' => Adw.vermelho,
      'abstencao' || 'obstrucao' => Adw.amarelo,
      'presidente' || 'presente_sem_voto' => Adw.azul,
      _ => Colors.grey,
    };

class EtiquetaVoto extends StatelessWidget {
  final String voto;
  const EtiquetaVoto(this.voto, {super.key});
  @override
  Widget build(BuildContext context) => Etiqueta(votoRotulo[voto] ?? voto, votoCor(voto));
}
