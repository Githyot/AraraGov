/// Medidas compartilhadas por todas as telas e por todos os estilos visuais.
///
/// Use sempre estes valores em vez de números soltos: é isso que mantém o
/// espaçamento igual de uma tela para outra. O que muda entre GNOME, Android,
/// Apple e Windows (raio dos cantos, cores de fundo, fonte) fica em
/// `Visual` (lib/tema/estilo.dart), nunca aqui.
abstract final class Esp {
  static const xxs = 2.0;
  static const xs = 4.0;
  static const p = 8.0;
  static const m = 12.0;
  static const g = 16.0;
  static const gg = 24.0;
  static const xg = 32.0;

  /// Espaço entre um grupo de linhas e o próximo.
  static const entreGrupos = gg;

  /// Margem lateral do conteúdo das telas.
  static const margem = m;
}

/// Tamanhos de ícone e de foto.
abstract final class Tam {
  static const icone = 20.0;
  static const iconePequeno = 16.0;
  static const avatar = 40.0;
  static const avatarGrande = 72.0;
  static const mascote = 128.0;
}
