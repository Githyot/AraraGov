/// Leitor do formato araragov-md/1 (docs/formato-md.md).
///
/// Um documento tem um cabeçalho plano (`chave: valor`) e tabelas marcadas
/// por `<!-- tabela: id -->`. Todo o resto é texto livre e é ignorado.
library;

const formatoMd = 'araragov-md/1';

class ErroFormatoMd implements Exception {
  ErroFormatoMd(this.mensagem);
  final String mensagem;

  @override
  String toString() => 'ErroFormatoMd: $mensagem';
}

class DocumentoMd {
  DocumentoMd(this.meta, this.tabelas, this.colunas);

  final Map<String, String> meta;

  /// Células vazias viram `null` ("sem dado", nunca zero).
  final Map<String, List<Map<String, String?>>> tabelas;
  final Map<String, List<String>> colunas;

  List<Map<String, String?>> tabela(String id) => tabelas[id] ?? const [];
}

final _marca = RegExp(r'^<!--\s*tabela:\s*([^\s>]+)\s*-->$');
final _idTabela = RegExp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$');
final _nome = RegExp(r'^[a-z0-9_]+$');
final _separador = RegExp(r'^\|(:?-+:?\|)+$');

List<String> _dividir(String linha) {
  final corpo = linha.trim();
  if (corpo.length < 2 || !corpo.startsWith('|') || !corpo.endsWith('|')) {
    throw ErroFormatoMd('linha de tabela inválida: $linha');
  }
  final interno = corpo.substring(1, corpo.length - 1);
  final celulas = <String>[];
  final atual = StringBuffer();
  for (var i = 0; i < interno.length; i++) {
    final c = interno[i];
    if (c == r'\' && i + 1 < interno.length && interno[i + 1] == '|') {
      atual.write('|');
      i++;
    } else if (c == '|') {
      celulas.add(atual.toString().trim());
      atual.clear();
    } else {
      atual.write(c);
    }
  }
  celulas.add(atual.toString().trim());
  return celulas;
}

DocumentoMd lerMd(String texto) {
  final linhas = texto.replaceAll('\r\n', '\n').split('\n');
  if (linhas.isEmpty || linhas.first.trim() != '---') {
    throw ErroFormatoMd("o arquivo deve começar com '---'");
  }
  final meta = <String, String>{};
  var i = 1;
  while (true) {
    if (i >= linhas.length) {
      throw ErroFormatoMd("cabeçalho sem '---' de fechamento");
    }
    final linha = linhas[i++].trim();
    if (linha == '---') break;
    if (linha.isEmpty) continue;
    final pos = linha.indexOf(':');
    final chave = pos < 0 ? '' : linha.substring(0, pos).trim();
    if (!_nome.hasMatch(chave)) {
      throw ErroFormatoMd('linha de cabeçalho inválida: $linha');
    }
    meta[chave] = linha.substring(pos + 1).trim();
  }
  if (meta['formato'] != formatoMd) {
    throw ErroFormatoMd('formato não suportado: ${meta['formato']}');
  }
  if (!meta.containsKey('tipo')) throw ErroFormatoMd("cabeçalho sem 'tipo'");

  final tabelas = <String, List<Map<String, String?>>>{};
  final colunas = <String, List<String>>{};
  while (i < linhas.length) {
    final marca = _marca.firstMatch(linhas[i++].trim());
    if (marca == null) continue;
    final id = marca.group(1)!;
    if (!_idTabela.hasMatch(id) || tabelas.containsKey(id)) {
      throw ErroFormatoMd('id de tabela inválido ou repetido: $id');
    }
    if (i + 1 >= linhas.length) throw ErroFormatoMd('tabela $id incompleta');
    final nomes = _dividir(linhas[i]);
    if (!nomes.every(_nome.hasMatch)) {
      throw ErroFormatoMd('tabela $id: nomes de coluna inválidos');
    }
    if (!_separador.hasMatch(linhas[i + 1].replaceAll(' ', ''))) {
      throw ErroFormatoMd('tabela $id: falta a linha |---|');
    }
    i += 2;
    final registros = <Map<String, String?>>[];
    while (i < linhas.length && linhas[i].trim().startsWith('|')) {
      final celulas = _dividir(linhas[i]);
      if (celulas.length != nomes.length) {
        throw ErroFormatoMd('tabela $id, linha ${i + 1}: ${celulas.length} células, esperado ${nomes.length}');
      }
      registros.add({
        for (var k = 0; k < nomes.length; k++) nomes[k]: celulas[k].isEmpty ? null : celulas[k],
      });
      i++;
    }
    tabelas[id] = registros;
    colunas[id] = nomes;
  }
  return DocumentoMd(meta, tabelas, colunas);
}

/// Converte uma célula numérica (ponto decimal); vazio vira `null`.
double? numeroMd(String? valor) {
  if (valor == null) return null;
  final n = double.tryParse(valor);
  if (n == null) throw ErroFormatoMd('número inválido: $valor');
  return n;
}
