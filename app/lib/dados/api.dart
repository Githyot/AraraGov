import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;

import 'modelos.dart';

/// Lê a API estática do AraraGov.
///
/// Endereço padrão: GitHub Pages do repositório. Para desenvolver sem
/// internet, rode com `--dart-define=ARARAGOV_AMOSTRA=true` e o app usa os
/// dados de exemplo em assets/amostra.
class Api {
  static const base = String.fromEnvironment('ARARAGOV_API', defaultValue: 'https://githyot.github.io/AraraGov/v1');
  static const amostra = bool.fromEnvironment('ARARAGOV_AMOSTRA');

  final http.Client _http;
  final Map<String, Object> _cache = {};

  Api({http.Client? client}) : _http = client ?? http.Client();

  Future<dynamic> _json(String caminho) async {
    if (amostra) {
      return jsonDecode(await rootBundle.loadString('assets/amostra/v1/$caminho'));
    }
    final resp = await _http.get(Uri.parse('$base/$caminho')).timeout(const Duration(seconds: 30));
    if (resp.statusCode != 200) {
      throw ApiErro('O servidor respondeu ${resp.statusCode}.');
    }
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  Future<List<PoliticoResumo>> politicos() async {
    final cache = _cache['politicos'];
    if (cache is List<PoliticoResumo>) return cache;
    final lista = [for (final p in await _json('politicos.json') as List) PoliticoResumo.fromJson(p)];
    _cache['politicos'] = lista;
    return lista;
  }

  /// Detalhes das votações de um ano (proposição, ementa, resultado...).
  Future<Map<String, dynamic>> votacoesDoAno(int ano) async {
    final cache = _cache['votacoes:$ano'];
    if (cache is Map<String, dynamic>) return cache;
    final dados = Map<String, dynamic>.from(await _json('votacoes/$ano.json') as Map);
    _cache['votacoes:$ano'] = dados;
    return dados;
  }

  /// Completa os votos com os detalhes de cada votação, baixando um arquivo por ano.
  Future<List<VotoEmVotacao>> completarVotos(List<VotoEmVotacao> votos) async {
    final anos = {
      for (final v in votos)
        if (!v.temDetalhe && v.data != null && v.data!.length >= 4) int.parse(v.data!.substring(0, 4))
    };
    final detalhes = <String, dynamic>{};
    for (final ano in anos) {
      try {
        detalhes.addAll(await votacoesDoAno(ano));
      } catch (_) {
        // sem o arquivo do ano, o voto aparece sem os detalhes
      }
    }
    return [
      for (final v in votos)
        if (v.temDetalhe || detalhes[v.id] == null)
          v
        else
          VotoEmVotacao.compacto([v.id, v.data, v.voto, v.ladoSim, v.atencao == null ? 0 : 1], Map<String, dynamic>.from(detalhes[v.id]))
    ];
  }

  Future<Perfil> perfil(String id) async {
    final cache = _cache['perfil:$id'];
    if (cache is Perfil) return cache;
    final perfil = Perfil.fromJson(await _json('politicos/$id.json'));
    _cache['perfil:$id'] = perfil;
    return perfil;
  }
}

class ApiErro implements Exception {
  final String mensagem;
  ApiErro(this.mensagem);
  @override
  String toString() => mensagem;
}
