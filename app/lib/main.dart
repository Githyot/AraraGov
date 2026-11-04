import 'package:flutter/material.dart';

import 'dados/api.dart';
import 'tema.dart';
import 'telas/inicio.dart';

void main() => runApp(AraraGovApp(api: Api()));

class AraraGovApp extends StatelessWidget {
  final Api api;
  const AraraGovApp({super.key, required this.api});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'AraraGov',
        debugShowCheckedModeBanner: false,
        theme: temaAdwaita(Brightness.light),
        darkTheme: temaAdwaita(Brightness.dark),
        home: Inicio(api: api),
      );
}
