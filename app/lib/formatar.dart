/// Formatação em português do Brasil, sem dependências.
String reais(num? valor, {bool centavos = true}) {
  if (valor == null) return '—';
  final negativo = valor < 0;
  final partes = valor.abs().toStringAsFixed(centavos ? 2 : 0).split('.');
  final inteiro = partes[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');
  final texto = centavos ? 'R\$ $inteiro,${partes[1]}' : 'R\$ $inteiro';
  return negativo ? '-$texto' : texto;
}

/// Valores grandes de forma curta: R$ 1,2 mi, R$ 350 mil.
String reaisCurto(num valor) {
  if (valor.abs() >= 1e6) return 'R\$ ${(valor / 1e6).toStringAsFixed(1).replaceAll('.', ',')} mi';
  if (valor.abs() >= 1e3) return 'R\$ ${(valor / 1e3).round()} mil';
  return reais(valor, centavos: false);
}

String porcentagem(num valor, {bool sinal = false}) {
  final t = '${valor.abs().toStringAsFixed(1).replaceAll('.', ',')}%';
  if (!sinal) return t;
  return valor >= 0 ? '+$t' : '−$t';
}

const _meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

String data(String? iso) {
  if (iso == null || iso.length < 10) return '—';
  final d = DateTime.tryParse(iso);
  if (d == null) return iso;
  return '${d.day.toString().padLeft(2, '0')} ${_meses[d.month - 1]} ${d.year}';
}

String mesAno(String? iso) {
  final d = iso == null ? null : DateTime.tryParse(iso.length == 7 ? '$iso-01' : iso);
  if (d == null) return iso ?? '—';
  return '${_meses[d.month - 1]}/${d.year}';
}

/// "Fulano de Tal" -> "FT"
String iniciais(String nome) {
  final p = nome.split(RegExp(r'\s+')).where((x) => x.isNotEmpty).toList();
  if (p.isEmpty) return '?';
  return (p.first[0] + (p.length > 1 ? p.last[0] : '')).toUpperCase();
}

String semAcento(String t) {
  const de = 'áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ';
  const para = 'aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC';
  final b = StringBuffer();
  for (final c in t.split('')) {
    final i = de.indexOf(c);
    b.write(i >= 0 ? para[i] : c);
  }
  return b.toString();
}

const mesesCurtos = _meses;

/// "jan–out" para um intervalo de meses (1 a 12).
String intervaloMeses(int inicio, int fim) =>
    inicio == fim ? _meses[inicio - 1] : '${_meses[inicio - 1]}–${_meses[fim - 1]}';

/// Valor curto para eixo de gráfico, sem quebrar linha: "R$ 40 mi", "R$ 250 mil".
String reaisEixo(num valor) {
  String curto(double v) {
    final t = v.toStringAsFixed(v >= 10 || v == v.roundToDouble() ? 0 : 1);
    return t.replaceAll('.', ',');
  }

  final a = valor.abs();
  if (a >= 1e9) return 'R\$ ${curto(a / 1e9)} bi';
  if (a >= 1e6) return 'R\$ ${curto(a / 1e6)} mi';
  if (a >= 1e3) return 'R\$ ${curto(a / 1e3)} mil';
  return 'R\$ ${a.round()}';
}

const _minusculas = {
  'a',
  'à',
  'ao',
  'aos',
  'as',
  'às',
  'com',
  'da',
  'das',
  'de',
  'do',
  'dos',
  'e',
  'em',
  'na',
  'nas',
  'no',
  'nos',
  'o',
  'os',
  'ou',
  'para',
  'por',
  'sem',
  'um',
  'uma',
};

/// Nomes que as fontes publicam EM MAIÚSCULAS ficam em frase normal:
/// "PASSAGEM AÉREA - RPA" -> "Passagem aérea - RPA". Siglas curtas continuam maiúsculas.
String nomeLegivel(String nome) {
  var t = nome.trim();
  if (t.endsWith('.')) t = t.substring(0, t.length - 1).trimRight();
  if (t != t.toUpperCase() || t.toLowerCase() == t.toUpperCase()) return t;
  var primeira = true;
  return t
      .split(' ')
      .map((p) {
        final letras = p.replaceAll(RegExp(r'[^A-Za-zÀ-ÿ]'), '');
        String r;
        if (letras.isEmpty) {
          r = p;
        } else if (!primeira && letras.length <= 3 && !_minusculas.contains(letras.toLowerCase())) {
          r = p; // sigla, ex.: RPA, SP
        } else {
          final m = p.toLowerCase();
          r = primeira ? m[0].toUpperCase() + m.substring(1) : m;
        }
        if (letras.isNotEmpty) primeira = false;
        return r;
      })
      .join(' ');
}

/// Nome de pessoa publicado EM MAIÚSCULAS: "IAN GARCEZ DE OLIVEIRA" -> "Ian Garcez de Oliveira".
String nomePessoa(String nome) {
  final t = nome.trim();
  if (t != t.toUpperCase()) return t;
  var primeira = true;
  return t
      .split(RegExp(r'\s+'))
      .map((p) {
        final m = p.toLowerCase();
        final r = !primeira && _minusculas.contains(m) ? m : (m.isEmpty ? m : m[0].toUpperCase() + m.substring(1));
        primeira = false;
        return r;
      })
      .join(' ');
}
