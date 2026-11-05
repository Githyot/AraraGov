/// Modelos da API estática gerada por `araragov exportar`.
double _n(dynamic v) => v == null ? 0 : (v as num).toDouble();
double? _nn(dynamic v) => v == null ? null : (v as num).toDouble();

class PoliticoResumo {
  final String id, casa, cargo, nome;
  final String esfera, orgao;
  final String? partido, uf, foto;
  final bool emExercicio;

  /// Declara publicamente doar o salário ou parte dele (lista curada, com fonte).
  final bool doaSalario;

  PoliticoResumo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        casa = j['casa'],
        cargo = j['cargo'],
        nome = j['nome'],
        esfera = j['esfera'] ?? (j['casa'] == 'camara' || j['casa'] == 'senado' ? 'federal' : 'estadual'),
        orgao = j['orgao'] ?? '',
        partido = j['partido'],
        uf = j['uf'],
        foto = j['foto'],
        emExercicio = j['em_exercicio'] ?? false,
        doaSalario = j['doa_salario'] ?? false;

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
  /// Verdadeiro quando o valor é o teto legal, não o valor exato pago.
  final bool teto;
  final String? observacao;

  Salario.fromJson(Map<String, dynamic> j)
      : atual = _nn(j['atual']),
        teto = j['teto'] ?? false,
        observacao = j['observacao'],
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

  /// "esquerda" | "direita" | null: qual lado o "Sim" representou nessa votação.
  final String? ladoSim;

  /// Motivo de atenção (ex.: tema que afeta os próprios parlamentares), ou null.
  final String? atencao;

  /// Lado em que este parlamentar votou, quando a votação tem lado claro.
  String? get ladoDoVoto {
    if (ladoSim == null || (voto != 'sim' && voto != 'nao')) return null;
    if (voto == 'sim') return ladoSim;
    return ladoSim == 'esquerda' ? 'direita' : 'esquerda';
  }

  VotoEmVotacao.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        voto = j['voto'],
        data = j['data'],
        proposicao = j['proposicao'],
        descricao = j['descricao'],
        ementa = j['ementa'],
        resultado = j['resultado'],
        link = j['link'],
        partidoNaEpoca = j['partido_na_epoca'],
        ladoSim = j['lado_sim'],
        atencao = j['atencao'];
}

class Posicao {
  final double pctEsquerda, pctDireita;
  final String faixa;
  final int votacoes;
  final double? mediaPartido;
  final String? faixaPartido;

  Posicao.fromJson(Map<String, dynamic> j)
      : pctEsquerda = _n(j['pct_esquerda']),
        pctDireita = _n(j['pct_direita']),
        faixa = j['faixa'],
        votacoes = j['votacoes_consideradas'] ?? 0,
        mediaPartido = _nn(j['media_do_partido']),
        faixaPartido = j['faixa_do_partido'];
}

typedef AlinhamentoPartido = ({String partido, double pct, int votacoes});

AlinhamentoPartido _alinh(Map j) =>
    (partido: j['partido'] as String, pct: _n(j['pct']), votacoes: j['votacoes'] as int);

class Alinhamento {
  final List<AlinhamentoPartido> maisAlinhados, menosAlinhados;
  final AlinhamentoPartido? proprioPartido;

  Alinhamento.fromJson(Map<String, dynamic> j)
      : maisAlinhados = [for (final a in (j['mais_alinhados'] as List? ?? [])) _alinh(a)],
        menosAlinhados = [for (final a in (j['menos_alinhados'] as List? ?? [])) _alinh(a)],
        proprioPartido = j['proprio_partido'] == null ? null : _alinh(j['proprio_partido']);
}

class Assessor {
  final String nome;
  final String? cargo, nivel, desde;
  final double? remuneracao;

  Assessor.fromJson(Map<String, dynamic> j)
      : nome = j['nome'],
        cargo = j['cargo'],
        nivel = j['nivel'],
        desde = j['desde'],
        remuneracao = _nn(j['remuneracao']);
}

class CustoGabinete {
  final double mensal;
  final int pessoasComValor, pessoas;
  final String? referencia;

  /// "folha" (soma das remunerações) ou "verba_gabinete" (verba gasta no mês).
  final String origem;

  CustoGabinete.fromJson(Map<String, dynamic> j)
      : mensal = _n(j['mensal']),
        pessoasComValor = j['pessoas_com_valor'] ?? 0,
        pessoas = j['pessoas'] ?? 0,
        referencia = j['referencia'],
        origem = j['origem'] ?? 'folha';
}

/// Valores mensais somados por ano: salário pago, verba de gabinete gasta.
class ValoresMensais {
  final double total;
  final List<({int ano, double valor})> porAno;
  final Map<int, ({double total, List<({int mes, double valor})> porMes})> anos;

  ValoresMensais.fromJson(Map<String, dynamic> j)
      : total = _n(j['total']),
        porAno = [for (final a in (j['por_ano'] as List? ?? [])) (ano: a['ano'] as int, valor: _n(a['valor']))],
        anos = {
          for (final e in (j['anos'] as Map? ?? {}).entries)
            int.parse(e.key as String): (
              total: _n(e.value['total']),
              porMes: [for (final m in (e.value['por_mes'] as List? ?? [])) (mes: m['mes'] as int, valor: _n(m['valor']))],
            )
        };

  int? get ultimoAno => anos.isEmpty ? null : anos.keys.reduce((a, b) => a > b ? a : b);
}

class Emendas {
  final double totalEmpenhado, totalPago;
  final int quantidade;
  final List<({int ano, double valor})> porAno;
  final List<NomeValor> porArea, porLocal;
  final List<({String nome, String? municipio, String? uf, double valor})> favorecidos;

  Emendas.fromJson(Map<String, dynamic> j)
      : totalEmpenhado = _n(j['total_empenhado']),
        totalPago = _n(j['total_pago']),
        quantidade = j['quantidade'] ?? 0,
        porAno = [for (final a in (j['por_ano'] as List? ?? [])) (ano: a['ano'] as int, valor: _n(a['empenhado']))],
        porArea = [for (final a in (j['por_area'] as List? ?? [])) (nome: a['nome'] as String, valor: _n(a['valor']))],
        porLocal = [for (final a in (j['por_local'] as List? ?? [])) (nome: a['nome'] as String, valor: _n(a['valor']))],
        favorecidos = [
          for (final f in (j['favorecidos'] as List? ?? []))
            (nome: f['nome'] as String, municipio: f['municipio'] as String?, uf: f['uf'] as String?, valor: _n(f['valor']))
        ];
}

class Beneficio {
  final String tipo, descricao;
  final double? valorMensal, valorAno;
  final int? ano;
  final String? referencia, fonte;

  Beneficio.fromJson(Map<String, dynamic> j)
      : tipo = j['tipo'],
        descricao = j['descricao'],
        valorMensal = _nn(j['valor_mensal']),
        valorAno = _nn(j['valor_ano']),
        ano = j['ano'],
        referencia = j['referencia'],
        fonte = j['fonte'];
}

/// Doação do salário declarada pelo próprio político, com a fonte pública.
class DoacaoSalario {
  final String? parte, data;
  final String descricao, fonte;

  DoacaoSalario.fromJson(Map<String, dynamic> j)
      : parte = j['parte'],
        data = j['data'],
        descricao = j['descricao'] ?? '',
        fonte = j['fonte'] ?? '';

  String get titulo => parte == null ? 'Declara doar o salário' : 'Declara doar $parte do salário';
}

class Perfil {
  final PoliticoResumo resumo;
  final String? nomeCivil, email, avisoCadastro;
  final Salario salario;
  final Gastos gastos;
  final Map<String, int> presenca;
  final List<VotoEmVotacao> votacoes;
  final List<Assessor> gabinete;
  final CustoGabinete? custoGabinete;
  final ValoresMensais? verbaGabinete, salarioPago;
  final List<Beneficio> beneficios;
  final Emendas? emendas;
  final DoacaoSalario? doacaoSalario;
  final Posicao? posicao;
  final Alinhamento? alinhamento;
  final ({int votacoes, int votouSim, int votouNao})? atencao;

  /// Ano do filtro de período, ou null para todo o período.
  final int? ano;
  final Map<String, dynamic> _json;

  Perfil.fromJson(Map<String, dynamic> j, {this.ano})
      : _json = j,
        resumo = PoliticoResumo.fromJson(j),
        nomeCivil = j['nome_civil'],
        email = j['email'],
        avisoCadastro = j['aviso_cadastro'],
        salario = Salario.fromJson(j['salario'] ?? {}),
        gastos = Gastos.fromJson(j['gastos'] ?? {}),
        presenca = {for (final e in (j['presenca'] as Map? ?? {}).entries) e.key as String: e.value as int},
        votacoes = [for (final v in (j['votacoes'] as List? ?? [])) VotoEmVotacao.fromJson(v)],
        gabinete = [for (final a in (j['gabinete'] as List? ?? [])) Assessor.fromJson(a)],
        custoGabinete = j['custo_gabinete'] == null ? null : CustoGabinete.fromJson(j['custo_gabinete']),
        verbaGabinete = j['verba_gabinete'] == null ? null : ValoresMensais.fromJson(j['verba_gabinete']),
        salarioPago = j['salario_pago'] == null ? null : ValoresMensais.fromJson(j['salario_pago']),
        beneficios = [for (final b in (j['beneficios'] as List? ?? [])) Beneficio.fromJson(b)],
        emendas = j['emendas'] == null ? null : Emendas.fromJson(j['emendas']),
        doacaoSalario = j['doacao_salario'] == null ? null : DoacaoSalario.fromJson(j['doacao_salario']),
        posicao = j['posicao'] == null ? null : Posicao.fromJson(j['posicao']),
        alinhamento = j['alinhamento'] == null ? null : Alinhamento.fromJson(j['alinhamento']),
        atencao = j['atencao'] == null
            ? null
            : (
                votacoes: j['atencao']['votacoes'] as int,
                votouSim: j['atencao']['votou_sim'] as int,
                votouNao: j['atencao']['votou_nao'] as int,
              );

  /// Anos que têm algum dado (votações, gastos ou emendas), do mais recente.
  List<int> get anosDisponiveis {
    final base = Perfil.fromJson(_json);
    final anos = <int>{
      for (final v in base.votacoes)
        if (v.data != null && v.data!.length >= 4) int.parse(v.data!.substring(0, 4)),
      for (final a in base.gastos.porAno) a.ano,
      for (final a in base.emendas?.porAno ?? const <({int ano, double valor})>[]) a.ano,
      ...?base.verbaGabinete?.anos.keys,
    };
    return anos.toList()..sort((a, b) => b.compareTo(a));
  }

  /// O mesmo perfil, só com o que aconteceu em [ano] (null = todo o período).
  /// Posição e alinhamento continuam calculados sobre todo o período.
  Perfil noAno(int? ano) {
    if (ano == null) return Perfil.fromJson(_json);
    final j = Map<String, dynamic>.from(_json);
    final chave = '$ano';
    final votos = [
      for (final v in (j['votacoes'] as List? ?? []))
        if ((v['data'] as String? ?? '').startsWith(chave)) v
    ];
    j['votacoes'] = votos;
    final presenca = <String, int>{};
    for (final v in votos) {
      presenca[v['voto'] as String] = (presenca[v['voto']] ?? 0) + 1;
    }
    j['presenca'] = presenca;
    final comAtencao = votos.where((v) => v['atencao'] != null).toList();
    j['atencao'] = comAtencao.isEmpty
        ? null
        : {
            'votacoes': comAtencao.length,
            'votou_sim': comAtencao.where((v) => v['voto'] == 'sim').length,
            'votou_nao': comAtencao.where((v) => v['voto'] == 'nao').length,
          };
    final g = Map<String, dynamic>.from(j['gastos'] as Map? ?? {});
    final doAno = (g['anos'] as Map?)?[chave] as Map?;
    j['gastos'] = {
      'total': doAno?['total'] ?? 0,
      'por_ano': [for (final a in (g['por_ano'] as List? ?? [])) if (a['ano'] == ano) a],
      'por_categoria': doAno?['por_categoria'] ?? [],
      'maiores_fornecedores': doAno?['maiores_fornecedores'] ?? [],
      'vs_inflacao': [for (final v in (g['vs_inflacao'] as List? ?? [])) if (v['ano'] == ano) v],
      'documentos_recentes': [
        for (final d in (g['documentos_recentes'] as List? ?? []))
          if ((d['data'] as String? ?? '').startsWith(chave)) d
      ],
    };
    final beneficiosAno = (j['beneficios_anos'] as Map?)?[chave];
    if (beneficiosAno != null) j['beneficios'] = beneficiosAno;
    for (final campo in ['verba_gabinete', 'salario_pago']) {
      final doAno = ((j[campo] as Map?)?['anos'] as Map?)?[chave] as Map?;
      j[campo] = doAno == null
          ? null
          : {
              'total': doAno['total'],
              'por_ano': [
                {'ano': ano, 'valor': doAno['total']}
              ],
              'anos': {chave: doAno},
            };
    }
    final e = j['emendas'] as Map?;
    final emAno = (e?['anos'] as Map?)?[chave] as Map?;
    j['emendas'] = emAno == null ? null : (Map<String, dynamic>.from(emAno)..['por_ano'] = []);
    return Perfil.fromJson(j, ano: ano);
  }

  int get totalVotacoes => presenca.values.fold(0, (a, b) => a + b);
  int get participou => ['sim', 'nao', 'abstencao', 'obstrucao', 'presidente', 'presente_sem_voto']
      .fold(0, (a, k) => a + (presenca[k] ?? 0));
}
