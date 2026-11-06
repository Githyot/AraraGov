import 'package:flutter/material.dart';

export 'tema/aparencia.dart';
export 'tema/estilo.dart';
export 'tema/temas.dart';
export 'tema/tokens.dart';

/// Cores com significado e medidas gerais. São as mesmas em todos os estilos
/// visuais (GNOME, Android, Apple, Windows), para que uma cor queira dizer a
/// mesma coisa em qualquer aparelho. O tema de cada sistema fica em lib/tema/.
class Adw {
  static const verde = Color(0xFF26A269); // accent: verde da bandeira, tom Adwaita
  static const verdeEscuro = Color(0xFF2EC27E);
  static const vermelho = Color(0xFFE01B24);
  static const amarelo = Color(0xFFE5A50A);
  static const azul = Color(0xFF3584E4);
  static const roxo = Color(0xFF9141AC);

  static const raio = 12.0; // cantos de cards e listas
  static const larguraMax = 720.0; // AdwClamp
  static const espaco = 12.0;
}
