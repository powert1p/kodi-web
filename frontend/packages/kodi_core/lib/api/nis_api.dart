import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/student.dart';
import '../models/stats.dart';
import '../models/graph_node.dart';
import '../models/problem.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  bool get isUnauthorized => statusCode == 401;
  bool get isForbidden => statusCode == 403;
  bool get isNotFound => statusCode == 404;
  bool get isServerError => statusCode != null && statusCode! >= 500;

  String get userMessage {
    if (isUnauthorized) return 'Неверный PIN или номер телефона';
    if (isForbidden) return 'Доступ запрещён';
    if (isNotFound) return 'Сервер не нашёл данные';
    if (isServerError) return 'Ошибка сервера — попробуйте позже';
    return message;
  }

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class NetworkException implements Exception {
  NetworkException(this.message);
  final String message;
  @override
  String toString() => message;
}

class NisApiClient {
  NisApiClient({required this.baseUrl, this.token});

  final String baseUrl;
  String? token;
  String lang = 'ru';

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store',
        'Pragma': 'no-cache',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<Map<String, dynamic>> post(
    String path,
    Map<String, dynamic> body,
  ) async => _post(path, body);

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final http.Response res;
    try {
      res = await http.post(
        Uri.parse('$baseUrl$path'),
        headers: _headers,
        body: jsonEncode(body),
      );
    } catch (e) {
      throw NetworkException(
        'Нет подключения к серверу. Проверьте интернет или попробуйте позже.');
    }
    final Map<String, dynamic> data;
    try {
      data = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw ApiException('Сервер вернул некорректный ответ',
          statusCode: res.statusCode);
    }
    if (res.statusCode >= 400) {
      throw ApiException(
        data['detail']?.toString() ?? 'Ошибка запроса',
        statusCode: res.statusCode,
      );
    }
    return data;
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final http.Response res;
    try {
      res = await http.get(
        Uri.parse('$baseUrl$path'),
        headers: _headers,
      );
    } catch (e) {
      throw NetworkException(
        'Нет подключения к серверу. Проверьте интернет или попробуйте позже.');
    }
    final Map<String, dynamic> data;
    try {
      data = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw ApiException('Сервер вернул некорректный ответ',
          statusCode: res.statusCode);
    }
    if (res.statusCode >= 400) {
      throw ApiException(
        data['detail']?.toString() ?? 'Ошибка запроса',
        statusCode: res.statusCode,
      );
    }
    return data;
  }

  // ── Auth ──────────────────────────────────────────────────────

  Future<String> loginWithTelegram(Map<String, dynamic> tgData) async {
    final res = await _post('/api/auth/telegram', tgData);
    token = res['access_token'] as String;
    return token!;
  }

  Future<bool> checkPhone(String phone) async {
    final res = await _post('/api/auth/phone/check', {'phone': phone, 'pin': ''});
    return res['exists'] as bool;
  }

  Future<String> phoneRegister(String phone, String name, String pin) async {
    final res = await _post('/api/auth/phone/register', {
      'phone': phone, 'name': name, 'pin': pin,
    });
    token = res['access_token'] as String;
    return token!;
  }

  Future<String> phoneLogin(String phone, String pin) async {
    final res = await _post('/api/auth/phone/login', {
      'phone': phone, 'pin': pin,
    });
    token = res['access_token'] as String;
    return token!;
  }

  Future<Student> getMe() async {
    final res = await _get('/api/auth/me');
    return Student.fromJson(res);
  }

  // ── Stats & Graph ─────────────────────────────────────────────

  Future<Stats> getStats() async {
    final res = await _get('/api/stats/me?lang=$lang');
    return Stats.fromJson(res);
  }

  Future<Map<String, dynamic>> getGraphData() async {
    return await _get('/api/graph/me?lang=$lang');
  }

  Future<List<GraphNode>> getGraphNodes() async {
    final data = await getGraphData();
    final nodes = data['nodes'] as List<dynamic>;
    return nodes
        .map((n) => GraphNode.fromJson(n as Map<String, dynamic>))
        .toList();
  }

  // ── Practice ──────────────────────────────────────────────────

  Future<Problem> getNextProblem({int count = 1, String? tag, String? nodeId}) async {
    final params = 'count=$count&lang=ru${tag != null ? '&tag=$tag' : ''}${nodeId != null ? '&node_id=$nodeId' : ''}';
    final res = await _get('/api/practice/next?$params');
    return Problem.fromJson(res);
  }

  Future<AnswerResult> submitAnswer(int problemId, String answer) async {
    final res = await _post('/api/practice/answer?lang=$lang', {
      'problem_id': problemId,
      'answer': answer,
    });
    return AnswerResult.fromJson(res);
  }

  Future<void> skipProblem(int problemId) async {
    await _post('/api/practice/skip', {
      'problem_id': problemId,
      'answer': '',
    });
  }

  // ── Diagnostic ──────────────────────────────────────────────

  Future<Map<String, dynamic>> startDiagnostic({String mode = 'exam'}) async {
    return await _post('/api/diagnostic/start', {'mode': mode});
  }

  Future<Map<String, dynamic>> getDiagnosticQuestion() async {
    return await _get('/api/diagnostic/question');
  }

  Future<Map<String, dynamic>> submitDiagnosticAnswer({
    required int problemId,
    required String answer,
    double elapsedSec = 30.0,
  }) async {
    return await _post('/api/diagnostic/answer', {
      'problem_id': problemId,
      'answer': answer,
      'elapsed_sec': elapsedSec,
    });
  }

  Future<Map<String, dynamic>> finishDiagnostic() async {
    return await _post('/api/diagnostic/finish', {});
  }

  Future<Map<String, dynamic>> getDiagnosticStatus() async {
    return await _get('/api/diagnostic/status');
  }

  Future<Map<String, dynamic>> cancelDiagnostic() async {
    return await _post('/api/diagnostic/cancel', {});
  }
}