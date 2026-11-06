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

/// Sim e Não usam roxo e marrom de propósito: verde e vermelho sugeririam
/// "certo" e "errado", e vermelho e azul já são as cores de esquerda e
/// direita. Os demais tipos ficam em cinza, nem a favor nem contra.
Color votoCor(String voto) => switch (voto) {
      'sim' => Adw.roxo,
      'nao' => Adw.marrom,
      _ => Colors.grey,
    };

class EtiquetaVoto extends StatelessWidget {
  final String voto;
  const EtiquetaVoto(this.voto, {super.key});
  @override
  Widget build(BuildContext context) => Etiqueta(votoRotulo[voto] ?? voto, votoCor(voto));
}
