import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config/app_runtime_config.dart';
import '../models/rag_stream.dart';

/// Gửi đánh giá 👍/👎 cho câu trả lời RAG qua staff-console BFF.
class RagFeedbackService {
  RagFeedbackService._();
  static final RagFeedbackService instance = RagFeedbackService._();

  final http.Client _client = http.Client();

  Uri get _uri {
    final base = AppRuntimeConfig.bffBaseUrl.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$base/api/student/rag-feedback');
  }

  String get _apiKey {
    if (AppRuntimeConfig.isBffConfigured) {
      return AppRuntimeConfig.studentApiKey;
    }
    return '';
  }

  bool get isConfigured => AppRuntimeConfig.isBffConfigured;

  Future<bool> submit({
    required String messageId,
    required String question,
    required String answer,
    required RagMessageRating rating,
    List<RetrievedContextPreview> contexts = const [],
    String? retrievalMode,
  }) async {
    if (!isConfigured) {
      if (kDebugMode) {
        debugPrint('[RagFeedback] BFF chưa cấu hình — bỏ qua gửi feedback');
      }
      return false;
    }
    if (rating == RagMessageRating.none) return false;

    final body = jsonEncode({
      'messageId': messageId,
      'question': question,
      'answer': answer,
      'rating': rating == RagMessageRating.up ? 'up' : 'down',
      'retrievedContexts': contexts.map((c) => c.toJson()).toList(),
      if (retrievalMode != null) 'retrievalMode': retrievalMode,
      'source': 'flutter_app',
    });

    try {
      final res = await _client.post(
        _uri,
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'X-Student-Key': _apiKey,
          'X-Student-Uid': AppRuntimeConfig.studentUid,
        },
        body: body,
      );
      if (kDebugMode) {
        debugPrint('[RagFeedback] status=${res.statusCode} body=${res.body}');
      }
      return res.statusCode >= 200 && res.statusCode < 300;
    } catch (e, st) {
      debugPrint('[RagFeedback] error: $e\n$st');
      return false;
    }
  }

  void close() => _client.close();
}
