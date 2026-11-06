import 'package:flutter/material.dart';

import 'dados/api.dart';
import 'tema.dart';
import 'telas/inicio.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(AraraGovApp(api: Api(), aparencia: await Aparencia.carregar()));
}

class AraraGovApp extends StatefulWidget {
  final Api api;
  final Aparencia? aparencia;
  const AraraGovApp({super.key, required this.api, this.aparencia});

  @override
  State<AraraGovApp> createState() => _AraraGovAppState();
}

class _AraraGovAppState extends State<AraraGovApp> {
  late final Aparencia _aparencia = widget.aparencia ?? Aparencia(salvar: false);

  @override
  Widget build(BuildContext context) => AparenciaEscopo(
    aparencia: _aparencia,
    child: ListenableBuilder(
      listenable: _aparencia,
      builder: (context, _) => MaterialApp(
        title: 'AraraGov',
        debugShowCheckedModeBanner: false,
        theme: temaPara(_aparencia.estilo, Brightness.light),
        darkTheme: temaPara(_aparencia.estilo, Brightness.dark),
        themeMode: _aparencia.modo,
        home: Inicio(api: widget.api),
      ),
    ),
  );
}
