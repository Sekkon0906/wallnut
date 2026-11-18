import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.status});

  final String message;
  final int? status;

  @override
  String toString() => message;
}

class WallnutApi {
  WallnutApi({http.Client? client}) : _client = client ?? http.Client();

  static const baseUrl = String.fromEnvironment(
    'WALLNUT_API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  final http.Client _client;
  final _transferRequests = <(String, int), String>{};
  String? _token;
  void Function()? onSessionExpired;

  Future<Member> login(String email, String password) async {
    final data = await _send('POST', '/session', {
      'email': email,
      'password': password,
    }) as Json;
    _token = data['token'] as String;
    return Member.fromJson(data['member'] as Json);
  }

  Future<void> logout() async {
    try {
      await _send('DELETE', '/session');
    } finally {
      _token = null;
      _transferRequests.clear();
    }
  }

  Future<List<Activity>> activities() =>
      _list('/activities', Activity.fromJson);
  Future<List<RankEntry>> ranking() => _list('/ranking', RankEntry.fromJson);

  Future<Wallet> wallet() async =>
      Wallet.fromJson(await _send('GET', '/wallet') as Json);

  Future<Attendance> attend(String activityId, String code) async =>
      Attendance.fromJson(
        await _send('POST', '/activities/$activityId/attendance', {
          'code': code,
        }) as Json,
      );

  Future<CheckinCode> issueCode(String activityId) async =>
      CheckinCode.fromJson(
        await _send('POST', '/activities/$activityId/code') as Json,
      );

  Future<void> transfer(String recipient, int points) async {
    final transfer = (recipient, points);
    final requestId = _transferRequests.putIfAbsent(
      transfer,
      () => const Uuid().v4(),
    );
    try {
      await _send('POST', '/transfers', {
        'recipient': recipient,
        'points': points,
        'request_id': requestId,
      });
      _transferRequests.remove(transfer);
    } on ApiException catch (error) {
      final status = error.status;
      if (status != null && status >= 400 && status < 500) {
        _transferRequests.remove(transfer);
      }
      rethrow;
    }
  }

  Future<String> askArdi(String message) async {
    final data =
        await _send('POST', '/ardi/messages', {'message': message}) as Json;
    return data['answer'] as String;
  }

  void close() => _client.close();

  Future<List<T>> _list<T>(String path, T Function(Json) decode) async {
    final rows = await _send('GET', path) as List;
    return rows.cast<Json>().map(decode).toList();
  }

  Future<Object?> _send(String method, String path, [Json? body]) async {
    final token = _token;
    final request = http.Request(method, Uri.parse('$baseUrl/v1$path'))
      ..headers['Accept'] = 'application/json';
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    if (body != null) {
      request.headers['Content-Type'] = 'application/json; charset=utf-8';
      request.bodyBytes = utf8.encode(jsonEncode(body));
    }

    final http.Response response;
    try {
      response = await _client
          .send(request)
          .then(http.Response.fromStream)
          .timeout(const Duration(seconds: 12));
    } on TimeoutException {
      throw const ApiException(
        'La conexión tardó demasiado. Intenta de nuevo.',
      );
    } on http.ClientException {
      throw const ApiException(
        'No pudimos conectar con Wallnut. Revisa tu conexión.',
      );
    }

    final status = response.statusCode;
    if (status == 204) return null;
    if (status == 401 && token != null && _token == token) {
      _token = null;
      _transferRequests.clear();
      onSessionExpired?.call();
    }

    final Object? data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      throw ApiException(
        'El servidor devolvió una respuesta inesperada.',
        status: status,
      );
    }

    if (status >= 400) {
      final detail = data is Json ? data['detail'] : null;
      final message = detail is String
          ? detail
          : 'Revisa los datos ingresados e intenta de nuevo.';
      throw ApiException(message, status: status);
    }
    return data;
  }
}
