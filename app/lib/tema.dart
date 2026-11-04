import 'package:flutter/material.dart';

/// Cores e medidas do Adwaita (GNOME Human Interface Guidelines).
/// https://developer.gnome.org/hig/
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

ThemeData temaAdwaita(Brightness brilho) {
  final escuro = brilho == Brightness.dark;
  final fundo = escuro ? const Color(0xFF222226) : const Color(0xFFFAFAFB);
  final card = escuro ? const Color(0xFF2E2E32) : Colors.white;
  final texto = escuro ? Colors.white : const Color(0xCC000006);
  final borda = escuro ? const Color(0x1AFFFFFF) : const Color(0x14000006);
  final accent = escuro ? Adw.verdeEscuro : Adw.verde;

  final esquema = ColorScheme.fromSeed(
    seedColor: accent,
    brightness: brilho,
    primary: accent,
    surface: fundo,
    onSurface: texto,
    error: Adw.vermelho,
  ).copyWith(surfaceContainer: card, surfaceContainerHigh: card, outlineVariant: borda);

  final base = ThemeData(useMaterial3: true, colorScheme: esquema, brightness: brilho);
  return base.copyWith(
    scaffoldBackgroundColor: fundo,
    appBarTheme: AppBarTheme(
      backgroundColor: fundo,
      foregroundColor: texto,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: true,
      titleTextStyle: base.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: texto),
      shape: Border(bottom: BorderSide(color: borda)),
    ),
    cardTheme: CardThemeData(
      color: card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Adw.raio),
        side: BorderSide(color: borda),
      ),
    ),
    dividerTheme: DividerThemeData(color: borda, space: 1, thickness: 1),
    listTileTheme: ListTileThemeData(
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      titleTextStyle: base.textTheme.bodyLarge?.copyWith(color: texto),
      subtitleTextStyle: base.textTheme.bodyMedium?.copyWith(color: texto.withValues(alpha: 0.55)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: escuro ? const Color(0x1AFFFFFF) : const Color(0x0F000006),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      isDense: true,
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: ButtonStyle(
        visualDensity: VisualDensity.compact,
        shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
      ),
    ),
  );
}
