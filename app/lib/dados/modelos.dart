/// Modelos da API estática gerada por `araragov exportar`.
double _n(dynamic v) => v == null ? 0 : (v as num).toDouble();
double? _nn(dynamic v) => v == null ? null : (v as num).toDouble();

class PoliticoResumo {
  final String id, casa, cargo, nome;
  final String? partido, uf, foto;
  final bool emExercicio;

  PoliticoResumo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        casa = j['casa'],
        cargo = j['cargo'],
        nome = j['nome'],
        partido = j['partido'],
        uf = j['uf'],
        foto = j['foto'],
        emExercicio = j['em_exercicio'] ?? false;

  String get partidoUf => [partido, uf].whereType<String>().join(' · ');
}

class ValorInflacao {
  final double valorInicial, valorAtual, corrigido, acimaPct;
  final String? desde;
  final int? ano;

  ValorInflacao.fromJson(Map<String, dynamic> j)
      : valorInicial = _n(j['valor_inicial']),
        valorAtual = _n(j['valor_atual'] ?? j['valor']),
        corrigido = _n(j['corrigido_pela_inflacao']),
        acimaPct = _n(j['acima_da_inflacao_pct']),
        desde = j['desde'],
        ano = j['ano'];
}

class Salario {
  final double? atual;
  final List<({String desde, double valor, String? ato, String? fonte})> historico;
  final ValorInflacao? vsInflacao;

  Salario.fromJson(Map<String, dynamic> j)
      : atual = _nn(j['atual']),
        historico = [
          for (final h in (j['historico'] as List? ?? []))
            (desde: h['desde'] as String, valor: _n(h['valor']), ato: h['ato'] as String?, fonte: h['fonte'] as String?)
        ],
        vsInflacao = j['vs_inflacao'] == null ? null : ValorInflacao.fromJson(j['vs_inflacao']);
}

typedef NomeValor = ({String nome, double valor});

class Gastos {
  final double total;
  final List<({int ano, double valor})> porAno;
  final List<NomeValor> porCategoria, maioresFornecedores;
  final List<ValorInflacao> vsInflacao;
  final List<Map<String, dynamic>> documentos;

  Gastos.fromJson(Map<String, dynamic> j)
      : total = _n(j['total']),
        porAno = [for (final a in (j['por_ano'] as List? ?? [])) (ano: a['ano'] as int, valor: _n(a['valor']))],
        porCategoria = [for (final c in (j['por_categoria'] as List? ?? [])) (nome: c['nome'] as String, valor: _n(c['valor']))],
        maioresFornecedores = [
          for (final c in (j['maiores_fornecedores'] as List? ?? [])) (nome: c['nome'] as String, valor: _n(c['valor']))
        ],
        vsInflacao = [for (final v in (j['vs_inflacao'] as List? ?? [])) ValorInflacao.fromJson(v)],
        documentos = [for (final d in (j['documentos_recentes'] as List? ?? [])) Map<String, dynamic>.from(d)];
}

class VotoEmVotacao {
  final String id, voto;
  final String? data, proposicao, descricao, ementa, resultado, link, partidoNaEpoca;

  VotoEmVotacao.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        voto = j['voto'],
        data = j['data'],
        proposicao = j['proposicao'],
        descricao = j['descricao'],
        ementa = j['ementa'],
        resultado = j['resultado'],
        link = j['link'],
        partidoNaEpoca = j['partido_na_epoca'];
}

class Assessor {
  final String nome;
  final String? cargo, nivel, desde;

  Assessor.fromJson(Map<String, dynamic> j)
      : nome = j['nome'],
        cargo = j['cargo'],
        nivel = j['nivel'],
        desde = j['desde'];
}

class Perfil {
  final PoliticoResumo resumo;
  final String? nomeCivil, email;
  final Salario salario;
  final Gastos gastos;
  final Map<String, int> presenca;
  final List<VotoEmVotacao> votacoes;
  final List<Assessor> gabinete;

  Perfil.fromJson(Map<String, dynamic> j)
      : resumo = PoliticoResumo.fromJson(j),
        nomeCivil = j['nome_civil'],
        email = j['email'],
        salario = Salario.fromJson(j['salario'] ?? {}),
        gastos = Gastos.fromJson(j['gastos'] ?? {}),
        presenca = {for (final e in (j['presenca'] as Map? ?? {}).entries) e.key as String: e.value as int},
        votacoes = [for (final v in (j['votacoes'] as List? ?? [])) VotoEmVotacao.fromJson(v)],
        gabinete = [for (final a in (j['gabinete'] as List? ?? [])) Assessor.fromJson(a)];

  int get totalVotacoes => presenca.values.fold(0, (a, b) => a + b);
  int get participou => ['sim', 'nao', 'abstencao', 'obstrucao', 'presidente', 'presente_sem_voto']
      .fold(0, (a, k) => a + (presenca[k] ?? 0));
}
