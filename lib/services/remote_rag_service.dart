import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';

/// Calls server-side RAG (`POST /v1/chat/stream`, SSE `data: {...}`).
class RemoteRagService {
  final http.Client _client = http.Client();

  static const _connectTimeout = Duration(seconds: 45);
  /// Khoảng lặng tối đa giữa hai phần dữ liệu từ server (chờ token đầu / giữa stream).
  static const _idleTimeout = Duration(seconds: 300);

  Stream<String> queryStream(String question, {String? docId}) async* {
    if (!ApiConfig.isRemoteConfigured) {
      yield 'Chưa cấu hình backend: thêm --dart-define=API_BASE_URL=... và STUDENT_API_KEY=...';
      return;
    }

    if (kDebugMode) {
      debugPrint(
        '[RemoteRag] POST ${ApiConfig.chatStreamUri} '
        '(base=${ApiConfig.apiBaseUrl})',
      );
    }

    final body = jsonEncode({
      'question': question,
      if (docId != null) 'doc_id': docId,
    });

    final req = http.Request('POST', ApiConfig.chatStreamUri)
      ..headers['Content-Type'] = 'application/json; charset=utf-8'
      ..headers['X-Student-Key'] = ApiConfig.studentApiKey
      ..body = body;

    http.StreamedResponse streamed;
    try {
      streamed = await _client.send(req).timeout(_connectTimeout);
    } on TimeoutException {
      yield 'Hết thời gian chờ kết nối (45 giây). Kiểm tra:\n'
          '• API_BASE_URL đúng IP máy Mac + :8080 (ví dụ http://192.168.1.42:8080)\n'
          '• Điện thoại và Mac cùng Wi‑Fi; tắt VPN trên điện thoại\n'
          '• Docker đang chạy: trên Mac gõ curl http://127.0.0.1:8080/health\n'
          '• Trên điện thoại mở Chrome thử http://<IP-Mac>:8080/health';
      return;
    } catch (e, st) {
      debugPrint('[RemoteRag] send error: $e\n$st');
      yield 'Không kết nối được tới server. Kiểm tra API_BASE_URL và mạng.\n$e';
      return;
    }

    if (kDebugMode) {
      debugPrint('[RemoteRag] status=${streamed.statusCode}');
    }

    if (streamed.statusCode != 200) {
      final r = await http.Response.fromStream(streamed);
      yield 'Lỗi HTTP ${streamed.statusCode}: ${r.body}';
      return;
    }

    final lineBuf = StringBuffer();
    try {
      await for (final chunk in streamed.stream
          .transform(utf8.decoder)
          .timeout(_idleTimeout)) {
        lineBuf.write(chunk);
        final raw = lineBuf.toString();
        if (!raw.contains('\n')) continue;
        final parts = raw.split('\n');
        lineBuf.clear();
        lineBuf.write(parts.removeLast());
        for (final rawLine in parts) {
          for (final out in _decodeSseLine(rawLine)) {
            if (out == _doneSentinel) return;
            yield out;
          }
        }
      }
    } on TimeoutException {
      yield '\n\n[Hết thời gian chờ dữ liệu từ server (5 phút). Có thể Gemini trên Docker đang chậm hoặc bị rate limit.]';
      return;
    }

    final tail = lineBuf.toString();
    for (final rawLine in tail.split('\n')) {
      for (final out in _decodeSseLine(rawLine)) {
        if (out == _doneSentinel) return;
        yield out;
      }
    }
  }

  static const String _doneSentinel = '\x00[DONE]\x00';

  /// Một dòng SSE; trả về các đoạn text hoặc [_doneSentinel] khi `[DONE]`.
  static Iterable<String> _decodeSseLine(String rawLine) sync* {
    final line = rawLine.trim();
    if (line.isEmpty) return;
    if (!line.startsWith('data:')) return;
    final payload = line.substring(5).trim();
    if (payload == '[DONE]') {
      yield _doneSentinel;
      return;
    }
    try {
      final map = jsonDecode(payload) as Map<String, dynamic>;
      if (map.containsKey('error')) {
        yield 'Lỗi server: ${map['error']}';
        yield _doneSentinel;
        return;
      }
      final text = map['text'] as String?;
      if (text != null && text.isNotEmpty) {
        yield text;
      }
    } catch (e) {
      debugPrint('[RemoteRag] bad SSE line: $payload → $e');
    }
  }

  void close() {
    _client.close();
  }
}
