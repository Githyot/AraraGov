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
