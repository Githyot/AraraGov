/// Endereços públicos do DivulgaCandContas, o portal de candidaturas do TSE.
///
/// O mesmo mapa existe na coleta (araragov/collectors/tse.py). O app monta os
/// endereços sozinho para que as fotos de prefeitos e vereadores apareçam com
/// os `resumo.md` já publicados, que têm `sq_candidato` e o código TSE do
/// município (`tse`), mas não a URL.
library;

const _divulga = 'https://divulgacandcontas.tse.jus.br/divulga';

/// Código de cada eleição no DivulgaCandContas (não é o CD_ELEICAO dos dados
/// abertos).
const eleicaoDivulgaCand = {
  '2016': '2',
  '2018': '2022802018',
  '2020': '2030402020',
  '2022': '2040602022',
  '2024': '2045202024',
};

final _numero = RegExp(r'^\d+$');

/// Foto da candidatura. `ue` é o código TSE do município (ou a UF, nas
/// eleições gerais). Sem dado suficiente, `null` (o app mostra as iniciais).
String? fotoTse(String? eleicao, String? sqCandidato, String? ue) {
  final id = eleicaoDivulgaCand[eleicao];
  if (id == null || sqCandidato == null || !_numero.hasMatch(sqCandidato) || ue == null || ue.isEmpty) return null;
  return '$_divulga/rest/arquivo/img/$id/$sqCandidato/$ue';
}

/// Página da candidatura: bens declarados, propostas, certidões e contas de
/// campanha.
String? paginaTse(String? eleicao, String? sqCandidato, String? ue) {
  final id = eleicaoDivulgaCand[eleicao];
  if (id == null || sqCandidato == null || !_numero.hasMatch(sqCandidato) || ue == null || ue.isEmpty) return null;
  return '$_divulga/#/candidato/$eleicao/$id/$ue/$sqCandidato';
}
