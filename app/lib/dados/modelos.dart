/// Modelos da API estática gerada por `araragov exportar`.
double _n(dynamic v) => v == null ? 0 : (v as num).toDouble();
double? _nn(dynamic v) => v == null ? null : (v as num).toDouble();

class PoliticoResumo {
  final String id, casa, cargo, nome;
  final String esfera, orgao;
  final String? partido, uf, foto;
  final bool emExercicio;

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

  CustoGabinete.fromJson(Map<String, dynamic> j)
      : mensal = _n(j['mensal']),
        pessoasComValor = j['pessoas_com_valor'] ?? 0,
        pessoas = j['pessoas'] ?? 0,
        referencia = j['referencia'];
}

class Beneficio {
  final String tipo, descricao;
  final double? valorMensal;
  final String? referencia, fonte;

  Beneficio.fromJson(Map<String, dynamic> j)
      : tipo = j['tipo'],
        descricao = j['descricao'],
        valorMensal = _nn(j['valor_mensal']),
        referencia = j['referencia'],
        fonte = j['fonte'];
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
  final List<Beneficio> beneficios;
  final Posicao? posicao;
  final Alinhamento? alinhamento;
  final ({int votacoes, int votouSim, int votouNao})? atencao;

  Perfil.fromJson(Map<String, dynamic> j)
      : resumo = PoliticoResumo.fromJson(j),
        nomeCivil = j['nome_civil'],
        email = j['email'],
        avisoCadastro = j['aviso_cadastro'],
        salario = Salario.fromJson(j['salario'] ?? {}),
        gastos = Gastos.fromJson(j['gastos'] ?? {}),
        presenca = {for (final e in (j['presenca'] as Map? ?? {}).entries) e.key as String: e.value as int},
        votacoes = [for (final v in (j['votacoes'] as List? ?? [])) VotoEmVotacao.fromJson(v)],
        gabinete = [for (final a in (j['gabinete'] as List? ?? [])) Assessor.fromJson(a)],
        custoGabinete = j['custo_gabinete'] == null ? null : CustoGabinete.fromJson(j['custo_gabinete']),
        beneficios = [for (final b in (j['beneficios'] as List? ?? [])) Beneficio.fromJson(b)],
        posicao = j['posicao'] == null ? null : Posicao.fromJson(j['posicao']),
        alinhamento = j['alinhamento'] == null ? null : Alinhamento.fromJson(j['alinhamento']),
        atencao = j['atencao'] == null
            ? null
            : (
                votacoes: j['atencao']['votacoes'] as int,
                votouSim: j['atencao']['votou_sim'] as int,
                votouNao: j['atencao']['votou_nao'] as int,
              );

  int get totalVotacoes => presenca.values.fold(0, (a, b) => a + b);
  int get participou => ['sim', 'nao', 'abstencao', 'obstrucao', 'presidente', 'presente_sem_voto']
      .fold(0, (a, k) => a + (presenca[k] ?? 0));
}
