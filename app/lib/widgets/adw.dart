import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../tema.dart';

/// Limita a largura do conteúdo e centraliza (AdwClamp).
class Clamp extends StatelessWidget {
  final Widget child;
  final double largura;
  const Clamp({super.key, required this.child, this.largura = Adw.larguraMax});

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(constraints: BoxConstraints(maxWidth: largura), child: child),
      );
}

/// Grupo com título e lista em caixa (AdwPreferencesGroup + boxed-list).
///
/// Desenha-se no jeito de cada sistema: lista em caixa com contorno (GNOME),
/// card tonal (Android), lista agrupada com título em maiúsculas (Apple) ou
/// card claro de cantos menores (Windows 11).
class Grupo extends StatelessWidget {
  final String? titulo, descricao;
  final Widget? acao;
  final List<Widget> filhos;
  const Grupo({super.key, this.titulo, this.descricao, this.acao, required this.filhos});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final v = Visual.of(context);
    final estiloTitulo = v.tituloGrupoMaiusculo
        ? tema.textTheme.bodySmall?.copyWith(color: v.corTituloGrupo, letterSpacing: 0.2)
        : tema.textTheme.titleSmall?.copyWith(
            fontWeight: v.estilo == EstiloVisual.android ? FontWeight.w500 : FontWeight.bold,
            color: v.corTituloGrupo,
          );
    final recuoTitulo = v.tituloGrupoMaiusculo || v.estilo == EstiloVisual.android ? Esp.g : Esp.xs;
    return Padding(
      padding: const EdgeInsets.only(bottom: Esp.entreGrupos),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (titulo != null)
            Padding(
              padding: EdgeInsets.fromLTRB(recuoTitulo, 0, Esp.xs, Esp.p),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(v.tituloGrupoMaiusculo ? titulo!.toUpperCase() : titulo!, style: estiloTitulo),
                    if (descricao != null)
                      Padding(
                        padding: const EdgeInsets.only(top: Esp.xxs),
                        child: Text(descricao!, style: tema.textTheme.bodySmall?.copyWith(color: v.corSecundaria)),
                      ),
                  ]),
                ),
                ?acao,
              ]),
            ),
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              for (var i = 0; i < filhos.length; i++) ...[
                if (i > 0) Divider(indent: v.recuoDivisor),
                filhos[i],
              ],
            ]),
          ),
        ],
      ),
    );
  }
}

/// Linha de lista (AdwActionRow): título, subtítulo e um valor/sufixo.
class Linha extends StatelessWidget {
  final String titulo;
  final String? subtitulo;
  final Widget? prefixo, sufixo;
  final String? valor;
  final VoidCallback? aoTocar;
  const Linha({super.key, required this.titulo, this.subtitulo, this.prefixo, this.sufixo, this.valor, this.aoTocar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final v = Visual.of(context);
    final avancar = Icon(v.iconeAvancar, size: v.apple ? 14 : Tam.icone, color: v.corSecundaria);
    return ListTile(
      leading: prefixo,
      title: Text(titulo),
      subtitle: subtitulo == null ? null : Text(subtitulo!),
      trailing: sufixo ??
          (valor == null
              ? (aoTocar == null ? null : avancar)
              : Text(
                  valor!,
                  style: tema.textTheme.bodyLarge?.copyWith(
                    color: v.apple ? v.corSecundaria : null,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                )),
      onTap: aoTocar,
    );
  }
}

/// Tela vazia, de erro ou de boas-vindas (AdwStatusPage), com a Arara.
class StatusPage extends StatelessWidget {
  final String mascote, titulo;
  final String? descricao;
  final Widget? acao;
  const StatusPage({super.key, required this.mascote, required this.titulo, this.descricao, this.acao});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(Esp.gg),
        child: Clamp(
          largura: 420,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            SvgPicture.asset('assets/mascote/arara-$mascote.svg', width: Tam.mascote, height: Tam.mascote),
            const SizedBox(height: Esp.gg),
            Text(titulo, textAlign: TextAlign.center, style: tema.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
            if (descricao != null) ...[
              const SizedBox(height: Esp.p),
              Text(descricao!, textAlign: TextAlign.center, style: tema.textTheme.bodyLarge?.copyWith(color: tema.hintColor)),
            ],
            if (acao != null) ...[const SizedBox(height: Esp.gg), acao!],
          ]),
        ),
      ),
    );
  }
}

/// Etiqueta pequena colorida (pill), usada para o voto.
class Etiqueta extends StatelessWidget {
  final String texto;
  final Color cor;
  const Etiqueta(this.texto, this.cor, {super.key});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: Esp.p + 2, vertical: Esp.xxs + 1),
        decoration: BoxDecoration(color: cor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(99)),
        child: Text(texto, style: TextStyle(color: cor, fontWeight: FontWeight.bold, fontSize: 12)),
      );
}

/// Foto do político, com iniciais enquanto carrega ou se não houver foto.
class Avatar extends StatelessWidget {
  final String? url;
  final String nome;
  final double tamanho;
  const Avatar({super.key, required this.url, required this.nome, this.tamanho = Tam.avatar});

  @override
  Widget build(BuildContext context) {
    final cor = Theme.of(context).colorScheme;
    final iniciais = nome.split(' ').where((p) => p.isNotEmpty).take(2).map((p) => p[0]).join().toUpperCase();
    final fallback = CircleAvatar(
      radius: tamanho / 2,
      backgroundColor: cor.primary.withValues(alpha: 0.14),
      child: Text(
        iniciais,
        style: TextStyle(color: cor.primary, fontSize: tamanho * 0.36, fontWeight: FontWeight.w600),
      ),
    );
    if (url == null) return fallback;
    return ClipOval(
      child: Image.network(
        url!.replaceFirst('http://', 'https://'),
        width: tamanho,
        height: tamanho,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => fallback,
        loadingBuilder: (_, child, progresso) => progresso == null ? child : fallback,
      ),
    );
  }
}
