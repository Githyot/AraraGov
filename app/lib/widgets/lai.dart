import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../tema.dart';

/// Pedido de documentos pela Lei de Acesso à Informação (Lei 12.527/2011).
///
/// O app só prepara o texto: quem envia é a própria pessoa, no e-SIC da
/// prefeitura ou no Fala.BR, com o próprio cadastro. Nada é enviado nem
/// guardado pelo AraraGov, e o app nunca pede CPF.
class PedidoLai {
  final String municipio, uf, assunto;
  final List<String> itens;
  const PedidoLai({required this.municipio, required this.uf, required this.assunto, this.itens = const []});

  String get orgao => 'Prefeitura Municipal de $municipio ($uf)';

  String get texto {
    final b = StringBuffer()
      ..writeln('À $orgao')
      ..writeln()
      ..writeln('Com base na Lei 12.527/2011 (Lei de Acesso à Informação), solicito cópia digital dos '
          'seguintes documentos sobre $assunto:')
      ..writeln();
    final pedidos = itens.isEmpty
        ? const ['Nota de empenho, nota de liquidação e ordem de pagamento', 'Contrato e aditivos', 'Notas fiscais e medições']
        : itens;
    for (var i = 0; i < pedidos.length; i++) {
      b.writeln('${i + 1}. ${pedidos[i]}');
    }
    b
      ..writeln()
      ..writeln('Peço que a resposta venha em formato digital, como prevê o art. 11, § 5º, e o art. 12 da lei '
          '(sem custo para cópias digitais). Caso algum documento não possa ser fornecido, peço que seja '
          'informado o motivo e a autoridade a quem posso recorrer (art. 11, § 4º).')
      ..writeln()
      ..writeln('Atenciosamente.');
    return b.toString();
  }

  Uri get buscaEsic => Uri.https('duckduckgo.com', '/', {'q': 'e-SIC prefeitura $municipio $uf acesso à informação'});
}

const _falaBr = 'https://falabr.cgu.gov.br/';

/// Mostra o texto pronto, com botões para copiar e abrir o canal de envio.
Future<void> mostrarPedidoLai(BuildContext context, PedidoLai pedido) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _PedidoLaiFolha(pedido),
    );

class _PedidoLaiFolha extends StatelessWidget {
  final PedidoLai pedido;
  const _PedidoLaiFolha(this.pedido);

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.85,
      builder: (context, rolagem) => ListView(
        controller: rolagem,
        padding: const EdgeInsets.all(Adw.espaco),
        children: [
          Text('Pedir documentos à prefeitura', style: tema.textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'O AraraGov só prepara o texto. Você envia pelo canal da prefeitura (e-SIC) ou pelo Fala.BR, '
            'com o seu cadastro. Nada é enviado nem guardado pelo app.',
            style: tema.textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(Adw.espaco),
              child: SelectableText(pedido.texto, style: tema.textTheme.bodyMedium),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            FilledButton.icon(
              icon: const Icon(Icons.copy),
              label: const Text('Copiar texto'),
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: pedido.texto));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Texto copiado')));
                }
              },
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.search),
              label: const Text('Procurar o e-SIC da prefeitura'),
              onPressed: () => launchUrl(pedido.buscaEsic),
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.open_in_new),
              label: const Text('Abrir o Fala.BR'),
              onPressed: () => launchUrl(Uri.parse(_falaBr)),
            ),
          ]),
          const SizedBox(height: 16),
          Text('Prazos', style: tema.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            '• A prefeitura tem 20 dias para responder, prorrogáveis por mais 10 com justificativa (art. 11).\n'
            '• Se negar ou não responder, você pode recorrer em 10 dias (art. 15).\n'
            '• Cópia digital não tem custo (art. 12).\n'
            '• O Fala.BR só atende prefeituras que aderiram a ele; nas outras, use o e-SIC do site da prefeitura.',
            style: tema.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
