import 'package:flutter/material.dart';

import 'estilo.dart';
import 'tokens.dart';

/// Paleta de superfícies e destaque de um estilo, num brilho (claro/escuro).
class _Paleta {
  final Color fundo, card, barra, texto, secundario, borda, divisor, destaque, sobreDestaque, campo;
  const _Paleta({
    required this.fundo,
    required this.card,
    required this.barra,
    required this.texto,
    required this.secundario,
    required this.borda,
    required this.divisor,
    required this.destaque,
    required this.sobreDestaque,
    required this.campo,
  });
}

/// Verde de destaque de cada sistema. É o verde da bandeira, no tom que cada
/// sistema usa para a cor de destaque, com contraste suficiente para texto.
_Paleta _paleta(EstiloVisual e, bool escuro) => switch ((e, escuro)) {
  // libadwaita 1.6+: window_bg, card_bg, headerbar_bg, accent verde.
  (EstiloVisual.gnome, false) => const _Paleta(
    fundo: Color(0xFFFAFAFB),
    card: Color(0xFFFFFFFF),
    barra: Color(0xFFFFFFFF),
    texto: Color(0xCC000006),
    secundario: Color(0x8C000006),
    borda: Color(0x14000006),
    divisor: Color(0x14000006),
    destaque: Color(0xFF26A269),
    sobreDestaque: Color(0xFFFFFFFF),
    campo: Color(0x0F000006),
  ),
  (EstiloVisual.gnome, true) => const _Paleta(
    fundo: Color(0xFF222226),
    card: Color(0xFF343438),
    barra: Color(0xFF2E2E32),
    texto: Color(0xFFFFFFFF),
    secundario: Color(0x8CFFFFFF),
    borda: Color(0x1AFFFFFF),
    divisor: Color(0x1AFFFFFF),
    destaque: Color(0xFF2EC27E),
    sobreDestaque: Color(0xFF000000),
    campo: Color(0x1AFFFFFF),
  ),
  // iOS: systemGroupedBackground, secondarySystemGroupedBackground,
  // separator, e o verde acessível do sistema.
  (EstiloVisual.apple, false) => const _Paleta(
    fundo: Color(0xFFF2F2F7),
    card: Color(0xFFFFFFFF),
    barra: Color(0xFFF2F2F7),
    texto: Color(0xFF000000),
    secundario: Color(0x993C3C43),
    borda: Color(0x00000000),
    divisor: Color(0x4A3C3C43),
    destaque: Color(0xFF248A3D),
    sobreDestaque: Color(0xFFFFFFFF),
    campo: Color(0x1F767680),
  ),
  (EstiloVisual.apple, true) => const _Paleta(
    fundo: Color(0xFF000000),
    card: Color(0xFF1C1C1E),
    barra: Color(0xFF000000),
    texto: Color(0xFFFFFFFF),
    secundario: Color(0x99EBEBF5),
    borda: Color(0x00000000),
    divisor: Color(0xA6545458),
    destaque: Color(0xFF30D158),
    sobreDestaque: Color(0xFF000000),
    campo: Color(0x3D767680),
  ),
  // Windows 11 (Fluent 2): fundo Mica, card com contorno fino.
  (EstiloVisual.windows, false) => const _Paleta(
    fundo: Color(0xFFF3F3F3),
    card: Color(0xFFFBFBFB),
    barra: Color(0xFFF3F3F3),
    texto: Color(0xE4000000),
    secundario: Color(0x9E000000),
    borda: Color(0x0F000000),
    divisor: Color(0x0F000000),
    destaque: Color(0xFF0F7B0F),
    sobreDestaque: Color(0xFFFFFFFF),
    campo: Color(0xB3FFFFFF),
  ),
  (EstiloVisual.windows, true) => const _Paleta(
    fundo: Color(0xFF202020),
    card: Color(0xFF2B2B2B),
    barra: Color(0xFF202020),
    texto: Color(0xFFFFFFFF),
    secundario: Color(0xC5FFFFFF),
    borda: Color(0x19000000),
    divisor: Color(0x15FFFFFF),
    destaque: Color(0xFF6CCB5F),
    sobreDestaque: Color(0xFF000000),
    campo: Color(0x0FFFFFFF),
  ),
  // Android usa o esquema Material 3 gerado a partir do verde (abaixo).
  _ => throw ArgumentError(e),
};

const _sementeAndroid = Color(0xFF1E8E3E);

/// Tema completo do app para um estilo e um brilho.
ThemeData temaPara(EstiloVisual estilo, Brightness brilho) {
  final e = estilo.resolver();
  return e == EstiloVisual.android ? _material3(brilho) : _desktopOuApple(e, brilho);
}

ThemeData _desktopOuApple(EstiloVisual e, Brightness brilho) {
  final escuro = brilho == Brightness.dark;
  final p = _paleta(e, escuro);
  final gnome = e == EstiloVisual.gnome, apple = e == EstiloVisual.apple, windows = e == EstiloVisual.windows;

  final raioCard = switch (e) {
    EstiloVisual.apple => 10.0,
    EstiloVisual.windows => 8.0,
    _ => 12.0,
  };
  final raioControle = switch (e) {
    EstiloVisual.apple => 10.0,
    EstiloVisual.windows => 4.0,
    _ => 6.0,
  };

  final esquema = ColorScheme.fromSeed(seedColor: p.destaque, brightness: brilho).copyWith(
    primary: p.destaque,
    onPrimary: p.sobreDestaque,
    surface: p.fundo,
    onSurface: p.texto,
    onSurfaceVariant: p.secundario,
    surfaceContainerLowest: p.card,
    surfaceContainerLow: p.card,
    surfaceContainer: p.card,
    surfaceContainerHigh: p.card,
    surfaceContainerHighest: p.campo,
    outline: p.secundario,
    outlineVariant: p.divisor,
    error: escuro ? const Color(0xFFFF7B63) : const Color(0xFFC01C28),
  );

  final fonte = switch (e) {
    EstiloVisual.gnome => 'Adwaita Sans',
    EstiloVisual.windows => 'Segoe UI Variable Text',
    _ => null, // Apple: o Flutter já usa a fonte do sistema (San Francisco).
  };
  final reserva = switch (e) {
    EstiloVisual.gnome => const ['Cantarell', 'Inter', 'Noto Sans', 'Roboto'],
    EstiloVisual.windows => const ['Segoe UI', 'Noto Sans', 'Roboto'],
    _ => null,
  };

  final base = ThemeData(
    useMaterial3: true,
    colorScheme: esquema,
    brightness: brilho,
    platform: e.plataforma,
    fontFamily: fonte,
    fontFamilyFallback: reserva,
    visualDensity: windows ? VisualDensity.compact : VisualDensity.standard,
    splashFactory: apple || windows ? NoSplash.splashFactory : InkSparkle.splashFactory,
  );
  // O textTheme do ThemeData não traz tamanhos (vêm só no Theme.of); junta
  // com a geometria padrão para os estilos fixos abaixo terem tamanho certo.
  final t = Typography.englishLike2021.merge(base.textTheme);

  final formaControle = RoundedRectangleBorder(borderRadius: BorderRadius.circular(raioControle));
  final botao = ButtonStyle(
    shape: WidgetStatePropertyAll(formaControle),
    elevation: const WidgetStatePropertyAll(0),
    textStyle: WidgetStatePropertyAll(t.labelLarge?.copyWith(fontWeight: windows ? FontWeight.w400 : FontWeight.w600)),
  );

  return base.copyWith(
    scaffoldBackgroundColor: p.fundo,
    canvasColor: p.fundo,
    hintColor: p.secundario,
    dividerColor: p.divisor,
    appBarTheme: AppBarTheme(
      backgroundColor: p.barra,
      surfaceTintColor: Colors.transparent,
      foregroundColor: p.texto,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: !windows,
      titleTextStyle: windows
          ? t.titleLarge?.copyWith(fontWeight: FontWeight.w600, color: p.texto, fontSize: 20)
          : t.titleMedium?.copyWith(
              fontWeight: apple ? FontWeight.w600 : FontWeight.bold,
              color: p.texto,
              fontSize: apple ? 17 : null,
            ),
      shape: gnome ? Border(bottom: BorderSide(color: p.borda)) : null,
    ),
    cardTheme: CardThemeData(
      color: p.card,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(raioCard),
        side: p.borda.a == 0 ? BorderSide.none : BorderSide(color: p.borda),
      ),
    ),
    dividerTheme: DividerThemeData(color: p.divisor, space: 1, thickness: apple ? 0.5 : 1),
    expansionTileTheme: ExpansionTileThemeData(
      shape: const Border(),
      collapsedShape: const Border(),
      iconColor: p.secundario,
      collapsedIconColor: p.secundario,
      textColor: p.texto,
      collapsedTextColor: p.texto,
    ),
    listTileTheme: ListTileThemeData(
      contentPadding: EdgeInsets.symmetric(horizontal: apple || windows ? Esp.g : Esp.m, vertical: Esp.xxs),
      minVerticalPadding: windows ? Esp.p : Esp.xs,
      titleTextStyle: t.bodyLarge?.copyWith(color: p.texto, fontSize: windows ? 14 : null),
      subtitleTextStyle: t.bodyMedium?.copyWith(color: p.secundario, fontSize: windows ? 12 : null),
      iconColor: p.secundario,
      selectedColor: p.destaque,
      selectedTileColor: p.destaque.withValues(alpha: 0.12),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: p.campo,
      hintStyle: TextStyle(color: p.secundario),
      prefixIconColor: p.secundario,
      border: windows
          ? UnderlineInputBorder(
              borderRadius: BorderRadius.circular(raioControle),
              borderSide: BorderSide(color: p.secundario.withValues(alpha: 0.4)),
            )
          : OutlineInputBorder(borderRadius: BorderRadius.circular(raioControle), borderSide: BorderSide.none),
      enabledBorder: windows
          ? UnderlineInputBorder(
              borderRadius: BorderRadius.circular(raioControle),
              borderSide: BorderSide(color: p.secundario.withValues(alpha: 0.4)),
            )
          : OutlineInputBorder(borderRadius: BorderRadius.circular(raioControle), borderSide: BorderSide.none),
      focusedBorder: windows
          ? UnderlineInputBorder(
              borderRadius: BorderRadius.circular(raioControle),
              borderSide: BorderSide(color: p.destaque, width: 2),
            )
          : OutlineInputBorder(
              borderRadius: BorderRadius.circular(raioControle),
              borderSide: BorderSide(color: p.destaque.withValues(alpha: gnome ? 0.5 : 0.0), width: 2),
            ),
      contentPadding: const EdgeInsets.symmetric(horizontal: Esp.m, vertical: Esp.m - 2),
      isDense: true,
    ),
    filledButtonTheme: FilledButtonThemeData(style: botao),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: botao.copyWith(side: WidgetStatePropertyAll(BorderSide(color: p.divisor))),
    ),
    textButtonTheme: TextButtonThemeData(style: botao),
    iconButtonTheme: IconButtonThemeData(
      style: ButtonStyle(shape: WidgetStatePropertyAll(gnome || windows ? formaControle : const CircleBorder())),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: ButtonStyle(
        visualDensity: VisualDensity.compact,
        shape: WidgetStatePropertyAll(formaControle),
        side: WidgetStatePropertyAll(BorderSide(color: p.divisor)),
        backgroundColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? (apple ? p.card : p.destaque.withValues(alpha: 0.15)) : p.campo,
        ),
        foregroundColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) && !apple ? p.destaque : p.texto,
        ),
      ),
    ),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(apple ? 99 : raioControle)),
      side: BorderSide(color: p.divisor),
      backgroundColor: p.campo,
      selectedColor: p.destaque.withValues(alpha: 0.15),
      checkmarkColor: p.destaque,
      labelStyle: t.labelLarge?.copyWith(color: p.texto),
    ),
    tabBarTheme: TabBarThemeData(
      labelColor: p.texto,
      unselectedLabelColor: p.secundario,
      indicatorColor: p.destaque,
      dividerColor: p.divisor,
      labelStyle: t.titleSmall?.copyWith(fontWeight: FontWeight.w600),
      indicatorSize: TabBarIndicatorSize.label,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: escuro && gnome ? p.barra : p.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(apple ? 14 : (windows ? 8 : 18))),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: escuro && gnome ? p.barra : p.card,
      surfaceTintColor: Colors.transparent,
      showDragHandle: true,
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: escuro && gnome ? p.barra : p.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(raioCard),
        side: BorderSide(color: p.divisor),
      ),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: escuro ? const Color(0xF2404044) : const Color(0xF2303034),
        borderRadius: BorderRadius.circular(raioControle),
      ),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: apple ? p.secundario : p.destaque),
    switchTheme: SwitchThemeData(
      thumbColor: const WidgetStatePropertyAll(Colors.white),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? p.destaque : p.campo),
      trackOutlineColor: const WidgetStatePropertyAll(Colors.transparent),
    ),
    radioTheme: RadioThemeData(
      fillColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? p.destaque : p.secundario),
    ),
    extensions: [
      Visual(
        estilo: e,
        raioCard: raioCard,
        raioControle: raioControle,
        bordaCard: p.borda.a != 0,
        tituloGrupoMaiusculo: apple,
        recuoDivisor: apple ? Esp.g : 0,
        iconeAvancar: iconeAvancarDe(e),
        corTituloGrupo: apple ? p.secundario : p.texto,
        corSecundaria: p.secundario,
      ),
    ],
  );
}

/// Material 3 (Android): esquema tonal gerado do verde, cards preenchidos
/// sem contorno, título da barra à esquerda.
ThemeData _material3(Brightness brilho) {
  final esquema = ColorScheme.fromSeed(seedColor: _sementeAndroid, brightness: brilho);
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: esquema,
    brightness: brilho,
    platform: TargetPlatform.android,
  );
  const raioCard = 20.0, raioControle = 99.0;
  final t = Typography.englishLike2021.merge(base.textTheme);
  final fundo = esquema.surface, card = esquema.surfaceContainer;
  return base.copyWith(
    scaffoldBackgroundColor: fundo,
    hintColor: esquema.onSurfaceVariant,
    appBarTheme: AppBarTheme(
      backgroundColor: fundo,
      scrolledUnderElevation: 2,
      centerTitle: false,
      titleTextStyle: t.titleLarge?.copyWith(color: esquema.onSurface),
    ),
    cardTheme: CardThemeData(
      color: card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(raioCard)),
    ),
    dividerTheme: DividerThemeData(color: esquema.outlineVariant.withValues(alpha: 0.6), space: 1, thickness: 1),
    expansionTileTheme: const ExpansionTileThemeData(shape: Border(), collapsedShape: Border()),
    listTileTheme: ListTileThemeData(
      contentPadding: const EdgeInsets.symmetric(horizontal: Esp.g, vertical: Esp.xs),
      titleTextStyle: t.bodyLarge?.copyWith(color: esquema.onSurface),
      subtitleTextStyle: t.bodyMedium?.copyWith(color: esquema.onSurfaceVariant),
      iconColor: esquema.onSurfaceVariant,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: esquema.surfaceContainerHigh,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(28), borderSide: BorderSide.none),
      contentPadding: const EdgeInsets.symmetric(horizontal: Esp.g, vertical: Esp.m),
      isDense: true,
    ),
    segmentedButtonTheme: const SegmentedButtonThemeData(style: ButtonStyle(visualDensity: VisualDensity.compact)),
    chipTheme: ChipThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
    bottomSheetTheme: const BottomSheetThemeData(showDragHandle: true),
    extensions: [
      Visual(
        estilo: EstiloVisual.android,
        raioCard: raioCard,
        raioControle: raioControle,
        bordaCard: false,
        tituloGrupoMaiusculo: false,
        recuoDivisor: 0,
        iconeAvancar: Icons.chevron_right,
        corTituloGrupo: esquema.primary,
        corSecundaria: esquema.onSurfaceVariant,
      ),
    ],
  );
}
