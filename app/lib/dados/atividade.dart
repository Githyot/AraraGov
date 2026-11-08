/// Atuação parlamentar e quadro de recursos dos deputados federais, como a
/// página de cada deputado na Câmara mostra (campos `atividade` e
/// `quadro_recursos` do perfil na API).
library;

/// Quadro "recursos" da página do deputado em um ano, inclusive o que ele
/// não usa ("Não faz uso", 0 viagens).
class QuadroRecursos {
  final int ano;
  final int? pessoal, pessoalAtivo, viagens;
  final String? imovel, auxilio, passaporte, fonte;
  final double? auxilioValor;

  QuadroRecursos.fromJson(this.ano, Map<String, dynamic> j)
      : pessoal = j['pessoal'],
        pessoalAtivo = j['pessoal_ativo'],
        viagens = j['viagens'],
        imovel = j['imovel'],
        auxilio = j['auxilio'],
        passaporte = j['passaporte'],
        fonte = j['fonte'],
        auxilioValor = (j['auxilio_valor'] as num?)?.toDouble();

  static Map<int, QuadroRecursos> lerAnos(Map? j) => {
        for (final e in (j ?? {}).entries) int.parse(e.key as String): QuadroRecursos.fromJson(int.parse(e.key as String), Map<String, dynamic>.from(e.value as Map)),
      };
}

class Proposta {
  final int id;
  final String rotulo, ementa;
  final String? data, situacao;
  final bool primeiroAutor;

  Proposta.fromLista(List l)
      : id = l[0] as int,
        rotulo = l[1] as String? ?? 'Proposta ${l[0]}',
        ementa = l[2] as String? ?? '',
        data = l[3] as String?,
        situacao = l[4] as String?,
        primeiroAutor = l[5] == 1;

  String get link => 'https://www.camara.leg.br/propostas-legislativas/$id';
}

class Relatoria {
  final int id;
  final String rotulo, ementa;
  final String? data, conclusao, situacao;

  Relatoria.fromLista(List l)
      : id = l[0] as int,
        rotulo = l[1] as String? ?? 'Proposta ${l[0]}',
        ementa = l[2] as String? ?? '',
        data = l[3] as String?,
        conclusao = l[4] as String?,
        situacao = l[5] as String?;

  String get link => 'https://www.camara.leg.br/propostas-legislativas/$id';
}

class Producao {
  final List<Proposta> propostas;
  final List<Relatoria> relatorias;
  final int emendas, requerimentos, pedidosInformacao;

  Producao.fromJson(Map j)
      : propostas = [for (final l in (j['propostas'] as List? ?? [])) Proposta.fromLista(l as List)],
        relatorias = [for (final l in (j['relatorias'] as List? ?? [])) Relatoria.fromLista(l as List)],
        emendas = j['emendas'] ?? 0,
        requerimentos = j['requerimentos'] ?? 0,
        pedidosInformacao = j['pedidos_informacao'] ?? 0;

  int get comoPrimeiroAutor => propostas.where((p) => p.primeiroAutor).length;
}

class Presenca {
  final int diasPresente, diasSessao;
  final bool periodoParcial;

  Presenca.fromJson(Map j)
      : diasPresente = j['dias_presente'] ?? 0,
        diasSessao = j['dias_sessao'] ?? 0,
        periodoParcial = j['periodo_parcial'] == true;

  double get pct => diasSessao == 0 ? 0 : diasPresente / diasSessao * 100;
}

class Discurso {
  final String? data, tipo, trecho, link;
  Discurso.fromLista(List l)
      : data = l[0] as String?,
        tipo = l[1] as String?,
        trecho = l[2] as String?,
        link = l[3] as String?;
}

class Discursos {
  final int total;
  final Map<String, int> porTipo;
  final List<Discurso> recentes;

  Discursos.fromJson(Map j)
      : total = j['total'] ?? 0,
        porTipo = {for (final e in (j['por_tipo'] as Map? ?? {}).entries) e.key as String: e.value as int},
        recentes = [for (final l in (j['recentes'] as List? ?? [])) Discurso.fromLista(l as List)];
}

class AtividadeAno {
  final Producao? producao;
  final Presenca? presenca;
  final Discursos? discursos;

  AtividadeAno.fromJson(Map j)
      : producao = j['producao'] == null ? null : Producao.fromJson(j['producao'] as Map),
        presenca = j['presenca'] == null ? null : Presenca.fromJson(j['presenca'] as Map),
        discursos = j['discursos'] == null ? null : Discursos.fromJson(j['discursos'] as Map);
}

class Comissao {
  final String? sigla, cargo, inicio, fim;
  final String nome;
  Comissao.fromLista(List l)
      : sigla = l[0] as String?,
        nome = l[1] as String? ?? '',
        cargo = l[2] as String?,
        inicio = l[3] as String?,
        fim = l[4] as String?;

  /// Sem data de saída, ou saída depois de hoje.
  bool get atual => fim == null || fim!.compareTo(DateTime.now().toIso8601String().substring(0, 10)) >= 0;
}

class Frente {
  final int? id;
  final String titulo;
  final bool coordena;
  Frente.fromLista(List l)
      : id = l[0] as int?,
        titulo = l[1] as String? ?? '',
        coordena = l[2] == 1;
}

class Atividade {
  final Map<int, AtividadeAno> anos;
  final List<Comissao> comissoes;
  final List<Frente> frentes;

  Atividade.fromJson(Map j)
      : anos = {
          for (final e in (j['anos'] as Map? ?? {}).entries) int.parse(e.key as String): AtividadeAno.fromJson(e.value as Map),
        },
        comissoes = [for (final l in ((j['comissoes'] as Map?)?['itens'] as List? ?? [])) Comissao.fromLista(l as List)],
        frentes = [for (final l in ((j['frentes'] as Map?)?['itens'] as List? ?? [])) Frente.fromLista(l as List)];

  /// O ano pedido, ou o mais recente com dados.
  int? anoMostrado(int? ano) {
    if (ano != null) return anos.containsKey(ano) ? ano : null;
    return anos.isEmpty ? null : anos.keys.reduce((a, b) => a > b ? a : b);
  }
}
