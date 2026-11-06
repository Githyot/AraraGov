import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'estilo.dart';

/// Escolhas de aparência da pessoa: estilo visual e modo claro/escuro.
/// Ficam salvas no aparelho.
class Aparencia extends ChangeNotifier {
  static const _chaveEstilo = 'aparencia.estilo', _chaveModo = 'aparencia.modo';

  EstiloVisual _estilo;
  ThemeMode _modo;
  final bool _salvar;

  Aparencia({EstiloVisual estilo = EstiloVisual.automatico, ThemeMode modo = ThemeMode.system, bool salvar = true})
    : _estilo = estilo, // ignore: prefer_initializing_formals
      _modo = modo, // ignore: prefer_initializing_formals
      _salvar = salvar; // ignore: prefer_initializing_formals

  EstiloVisual get estilo => _estilo;
  ThemeMode get modo => _modo;

  /// Lê o que foi salvo. Se não der (primeiro uso, plataforma sem suporte),
  /// fica no automático.
  static Future<Aparencia> carregar() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return Aparencia(
        estilo: EstiloVisual.values.asNameMap()[prefs.getString(_chaveEstilo)] ?? EstiloVisual.automatico,
        modo: ThemeMode.values.asNameMap()[prefs.getString(_chaveModo)] ?? ThemeMode.system,
      );
    } catch (_) {
      return Aparencia();
    }
  }

  set estilo(EstiloVisual e) {
    if (e == _estilo) return;
    _estilo = e;
    notifyListeners();
    _gravar(_chaveEstilo, e.name);
  }

  set modo(ThemeMode m) {
    if (m == _modo) return;
    _modo = m;
    notifyListeners();
    _gravar(_chaveModo, m.name);
  }

  Future<void> _gravar(String chave, String valor) async {
    if (!_salvar) return;
    try {
      (await SharedPreferences.getInstance()).setString(chave, valor);
    } catch (_) {}
  }
}

/// Dá acesso à [Aparencia] em qualquer tela.
class AparenciaEscopo extends InheritedNotifier<Aparencia> {
  const AparenciaEscopo({super.key, required Aparencia aparencia, required super.child}) : super(notifier: aparencia);

  static Aparencia of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<AparenciaEscopo>()!.notifier!;

  static Aparencia? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AparenciaEscopo>()?.notifier;
}
