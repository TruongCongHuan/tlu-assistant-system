// lib/services/student_api_client.dart
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_runtime_config.dart';

class StudentApiClient {
  StudentApiClient._();

  static Uri _uri(String path) {
    final base = AppRuntimeConfig.bffBaseUrl.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$base$path');
  }

  static Map<String, String> get _headers => {
        'X-Student-Key': AppRuntimeConfig.studentApiKey,
        'X-Student-Uid': AppRuntimeConfig.studentUid,
        'Content-Type': 'application/json',
      };

  static Future<Map<String, dynamic>> getJson(String path) async {
    final r = await http
        .get(_uri(path), headers: _headers)
        .timeout(const Duration(seconds: 15));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw StateError('API ${r.statusCode}: ${r.body}');
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final r = await http
        .post(_uri(path), headers: _headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 30));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw StateError('API ${r.statusCode}: ${r.body}');
    }
    if (r.body.isEmpty) return {};
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> postMultipart(
    String path, {
    required Map<String, String> fields,
    List<http.MultipartFile> files = const [],
  }) async {
    final req = http.MultipartRequest('POST', _uri(path));
    req.headers['X-Student-Key'] = AppRuntimeConfig.studentApiKey;
    req.headers['X-Student-Uid'] = AppRuntimeConfig.studentUid;
    req.fields.addAll(fields);
    req.files.addAll(files);
    final streamed = await req.send().timeout(const Duration(minutes: 2));
    final r = await http.Response.fromStream(streamed);
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw StateError('API ${r.statusCode}: ${r.body}');
    }
    if (r.body.isEmpty) return {};
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
