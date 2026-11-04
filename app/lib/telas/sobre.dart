import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:url_launcher/url_launcher.dart';

void mostrarSobre(BuildContext context) {
  final tema = Theme.of(context);
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      content: SizedBox(
        width: 360,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          SvgPicture.asset('assets/icone/araragov-arredondado.svg', width: 96, height: 96),
          const SizedBox(height: 12),
          Text('AraraGov', style: tema.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text(
            'Dados públicos de políticos brasileiros, organizados e fáceis de entender. '
            'O app é apenas informativo: não acusa ninguém e todo dado tem link para a fonte oficial.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 12),
          Text(
            'Fontes: Câmara dos Deputados, Senado Federal e Banco Central.\n'
            'Código aberto sob a licença AGPL-3.0.',
            textAlign: TextAlign.center,
            style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
          ),
        ]),
      ),
      actions: [
        TextButton(
          onPressed: () => launchUrl(Uri.parse('https://github.com/Githyot/AraraGov')),
          child: const Text('Código-fonte'),
        ),
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Fechar')),
      ],
    ),
  );
}
