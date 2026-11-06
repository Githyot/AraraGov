import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../dados/tse.dart';
import '../tema.dart';
import '../widgets/adw.dart';

/// Perfil de um prefeito, vice ou vereador, com o que o TSE publica.
///
/// Salário, gastos e votações das câmaras municipais ainda não são coletados;
/// a tela diz isso e quem deveria publicar, em vez de mostrar zero.
class PerfilMunicipalTela extends StatelessWidget {
  /// A linha da tabela `mandatos` do `resumo.md` que foi tocada.
  final Map<String, String?> mandato;

  /// Todas as linhas do município, para achar os outros mandatos da pessoa.
  final List<Map<String, String?>> mandatos;
  final String municipio, uf;

  /// Código TSE do município (unidade eleitoral).
  final String? ue;

  const PerfilMunicipalTela({
    super.key,
    required this.mandato,
    required this.mandatos,
    required this.municipio,
    required this.uf,
    required this.ue,
  });

  /// Mesma pessoa em outras eleições: o TSE muda o `sq_candidato` a cada
  /// eleição, então a ligação é pelo nome civil, só dentro do município.
  List<Map<String, String?>> get historico {
    final chave = chaveNome(mandato['nome_civil'] ?? mandato['nome']);
    if (chave.isEmpty) return [mandato];
    return mandatos.where((m) => chaveNome(m['nome_civil'] ?? m['nome']) == chave).toList()
      ..sort((a, b) => (b['eleicao'] ?? '').compareTo(a['eleicao'] ?? ''));
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final m = mandato;
    final nome = m['nome'] ?? '—';
    final cargo = m['cargo'] ?? '—';
    final pagina = paginaTse(m['eleicao'], m['sq_candidato'], ue);
    final camara = cargo == 'Vereador';
    return Scaffold(
      appBar: AppBar(title: Text(nome)),
      body: ListView(
        padding: const EdgeInsets.all(Adw.espaco),
        children: [
          Clamp(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Avatar(url: fotoTse(m['eleicao'], m['sq_candidato'], ue), nome: nome, tamanho: 112),
              const SizedBox(height: 12),
              Text(nome, textAlign: TextAlign.center, style: tema.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
              if (m['nome_civil'] != null && m['nome_civil'] != nome)
                Text(m['nome_civil']!, textAlign: TextAlign.center, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
              const SizedBox(height: 4),
              Text('$cargo · ${m['partido'] ?? '—'}', textAlign: TextAlign.center, style: tema.textTheme.bodyLarge),
              Text('$municipio ($uf) · mandato ${m['inicio'] ?? '?'}–${m['fim'] ?? '?'}',
                  textAlign: TextAlign.center, style: tema.textTheme.bodyMedium?.copyWith(color: tema.hintColor)),
              const SizedBox(height: 24),
              Grupo(
                titulo: 'Eleição de ${m['eleicao'] ?? '—'}',
                filhos: [
                  Linha(titulo: 'Número', valor: m['numero'] ?? '—'),
                  Linha(titulo: 'Partido na eleição', valor: m['partido'] ?? '—'),
                  if (m['situacao'] != null) Linha(titulo: 'Resultado', valor: m['situacao']),
                  if (pagina != null)
                    Linha(
                      prefixo: const Icon(Icons.open_in_new),
                      titulo: 'Ficha no TSE',
                      subtitulo: 'Bens declarados, propostas, certidões e contas de campanha',
                      aoTocar: () => launchUrl(Uri.parse(pagina)),
                    ),
                ],
              ),
              Grupo(
                titulo: 'Mandatos em $municipio',
                descricao: 'Ligados pelo nome registrado no TSE.',
                filhos: [
                  for (final h in historico)
                    Linha(
                      titulo: '${h['cargo'] ?? '—'} · ${h['inicio'] ?? '?'}–${h['fim'] ?? '?'}',
                      subtitulo: 'Eleição de ${h['eleicao'] ?? '—'} · ${h['partido'] ?? '—'}',
                    ),
                ],
              ),
              Grupo(
                titulo: 'Não há dados',
                filhos: [
                  ListTile(
                    leading: const Icon(Icons.info_outline),
                    title: Text(camara
                        ? 'Salário, verba de gabinete, assessores e votações deste vereador ainda não foram coletados'
                        : 'Salário, gastos de gabinete e equipe ainda não foram coletados'),
                    subtitle: Text(
                      'Responsável: ${camara ? 'Câmara Municipal' : 'Prefeitura'} de $municipio (esfera municipal)\n'
                      'Devem estar no portal da transparência, pela Lei de Acesso à Informação '
                      '(Lei 12.527/2011, art. 8º) e pela Lei Complementar 131/2009.',
                      style: tema.textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 0, 4, 24),
                child: Text(
                  'Fonte: Tribunal Superior Eleitoral. Quem assumiu depois da eleição (suplentes, '
                  'eleições suplementares) ainda não aparece.',
                  style: tema.textTheme.bodySmall?.copyWith(color: tema.hintColor),
                ),
              ),
            ]),
          ),
        ],
      ),
    );
  }
}

const _acentos = {
  'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
  'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i', 'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
  'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u', 'ç': 'c', 'ñ': 'n',
};

/// "Mário  Chotian" e "MARIO CHOTIAN" viram "mario chotian".
String chaveNome(String? nome) {
  final b = StringBuffer();
  for (final c in (nome ?? '').toLowerCase().split('')) {
    final s = _acentos[c] ?? c;
    b.write(RegExp(r'[a-z0-9]').hasMatch(s) ? s : ' ');
  }
  return b.toString().split(' ').where((p) => p.isNotEmpty).join(' ');
}
