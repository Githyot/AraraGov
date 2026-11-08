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
  static const marrom = Color(0xFF986A44);

  // Cores dos lados nas análises de posição. Usadas só para esquerda e
  // direita, sempre juntas e com o mesmo peso, para não sugerir julgamento.
  static const corEsquerda = vermelho;
  static const corDireita = azul;
  static Color corLado(String lado) => lado == 'esquerda' ? corEsquerda : corDireita;

  /// Cores para distinguir pessoas na comparação: as cores de destaque do
  /// libadwaita que não têm outro significado no app. Ficam de fora o verde
  /// (destaque do app), o roxo e o marrom (Sim e Não), o vermelho e o azul
  /// (esquerda e direita) e o amarelo (abstenção e atenção), e nenhuma
  /// remete a partido.
  static const pessoas = [
    Color(0xFF2190A4), // teal
    Color(0xFFED5B00), // laranja
    Color(0xFFD56199), // rosa
    Color(0xFF6F8396), // ardósia
  ];

  /// Cor da pessoa [i], clareada no tema escuro para manter o contraste.
  static Color pessoa(int i, Brightness brilho) {
    final c = pessoas[i % pessoas.length];
    return brilho == Brightness.dark ? Color.lerp(c, Colors.white, 0.25)! : c;
  }

  static const raio = 12.0; // cantos de cards e listas
  static const larguraMax = 720.0; // AdwClamp
  static const espaco = 12.0;
}
