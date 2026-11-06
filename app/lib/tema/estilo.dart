import 'dart:ui' show lerpDouble;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Estilo visual do app. Cada sistema tem o seu jeito: o app segue o do
/// aparelho por padrão, e a pessoa pode trocar em Aparência.
enum EstiloVisual {
  automatico('Automático', 'Segue o sistema do aparelho'),
  gnome('GNOME', 'Adwaita, como os apps do Linux'),
  android('Android', 'Material 3, como os apps do Google'),
  apple('Apple', 'Como os apps do iPhone e do Mac'),
  windows('Windows', 'Fluent, como os apps do Windows 11');

  final String rotulo, descricao;
  const EstiloVisual(this.rotulo, this.descricao);

  /// O estilo que vale de fato: troca "automático" pelo do sistema.
  EstiloVisual resolver([TargetPlatform? plataforma]) {
    if (this != automatico) return this;
    return switch (plataforma ?? defaultTargetPlatform) {
      TargetPlatform.android || TargetPlatform.fuchsia => android,
      TargetPlatform.iOS || TargetPlatform.macOS => apple,
      TargetPlatform.windows => windows,
      TargetPlatform.linux => gnome,
    };
  }

  /// Plataforma usada pelo Flutter para transições, rolagem e fontes.
  TargetPlatform get plataforma => switch (this) {
    android => TargetPlatform.android,
    apple => TargetPlatform.iOS,
    windows => TargetPlatform.windows,
    gnome || automatico => TargetPlatform.linux,
  };
}

/// Detalhes que mudam de um estilo para outro e que os widgets do app
/// (Grupo, Linha, Etiqueta...) consultam para se desenhar.
///
/// As cores com significado (Sim, Não, esquerda, direita, acima da inflação,
/// cores das pessoas na comparação) NÃO estão aqui: são as mesmas em todos os
/// estilos, para que o significado não mude ao trocar de sistema.
@immutable
class Visual extends ThemeExtension<Visual> {
  final EstiloVisual estilo;

  /// Raio dos cantos de cards e listas, e de botões e campos.
  final double raioCard, raioControle;

  /// Card com contorno fino (GNOME, Windows) ou só com cor de fundo.
  final bool bordaCard;

  /// Título do grupo em maiúsculas pequenas (Apple).
  final bool tituloGrupoMaiusculo;

  /// Recuo à esquerda do divisor entre linhas (Apple recua, os outros não).
  final double recuoDivisor;

  final IconData iconeAvancar;

  /// Cor dos títulos de grupo e do texto secundário (subtítulos, valores).
  final Color corTituloGrupo, corSecundaria;

  const Visual({
    required this.estilo,
    required this.raioCard,
    required this.raioControle,
    required this.bordaCard,
    required this.tituloGrupoMaiusculo,
    required this.recuoDivisor,
    required this.iconeAvancar,
    required this.corTituloGrupo,
    required this.corSecundaria,
  });

  static Visual of(BuildContext context) =>
      Theme.of(context).extension<Visual>() ??
      Visual(
        estilo: EstiloVisual.gnome,
        raioCard: 12,
        raioControle: 6,
        bordaCard: true,
        tituloGrupoMaiusculo: false,
        recuoDivisor: 0,
        iconeAvancar: Icons.chevron_right,
        corTituloGrupo: Theme.of(context).colorScheme.onSurface,
        corSecundaria: Theme.of(context).hintColor,
      );

  bool get apple => estilo == EstiloVisual.apple;

  @override
  Visual copyWith({EstiloVisual? estilo}) => Visual(
    estilo: estilo ?? this.estilo,
    raioCard: raioCard,
    raioControle: raioControle,
    bordaCard: bordaCard,
    tituloGrupoMaiusculo: tituloGrupoMaiusculo,
    recuoDivisor: recuoDivisor,
    iconeAvancar: iconeAvancar,
    corTituloGrupo: corTituloGrupo,
    corSecundaria: corSecundaria,
  );

  @override
  Visual lerp(Visual? other, double t) {
    if (other == null) return this;
    final base = t < 0.5 ? this : other;
    return Visual(
      estilo: base.estilo,
      raioCard: lerpDouble(raioCard, other.raioCard, t)!,
      raioControle: lerpDouble(raioControle, other.raioControle, t)!,
      bordaCard: base.bordaCard,
      tituloGrupoMaiusculo: base.tituloGrupoMaiusculo,
      recuoDivisor: lerpDouble(recuoDivisor, other.recuoDivisor, t)!,
      iconeAvancar: base.iconeAvancar,
      corTituloGrupo: Color.lerp(corTituloGrupo, other.corTituloGrupo, t)!,
      corSecundaria: Color.lerp(corSecundaria, other.corSecundaria, t)!,
    );
  }
}

/// Ícone de "abrir" no fim das linhas, no formato de cada sistema.
IconData iconeAvancarDe(EstiloVisual e) => switch (e) {
  EstiloVisual.apple => Icons.arrow_forward_ios_rounded,
  _ => Icons.chevron_right,
};
