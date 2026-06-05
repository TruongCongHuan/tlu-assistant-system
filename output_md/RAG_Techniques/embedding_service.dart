// lib/services/embedding_service.dart
import 'package:flutter/foundation.dart';
import 'package:google_generative_ai/google_generative_ai.dart';

class EmbeddingService {
  static const String _apiKey = String.fromEnvironment(
    'GEMINI_KEY',
    defaultValue: '',
  );
  static const String _model  = 'models/gemini-embedding-2-preview'; // Thêm prefix 'models/'

  late final GenerativeModel _embedModel;

  EmbeddingService() {
    _embedModel = GenerativeModel(model: _model, apiKey: _apiKey);
  }

  // ── Embed 1 text ─────────────────────────────────────
  Future<List<double>> embed(String text) async {
    if (_apiKey.isEmpty) {
      throw StateError(
        'Thiếu GEMINI_KEY. Chạy: flutter run --dart-define=GEMINI_KEY=...',
      );
    }
    try {
      final result = await _embedModel.embedContent(Content.text(text));
      return result.embedding.values;
    } catch (e) {
      debugPrint('[Embed] Error: $e');
      rethrow;
    }
  }

  // ── Batch embed với progress callback ─────────────────
  // Gemini free: 1500 req/ngày, 60 RPM → delay giữa các batch
  Future<List<List<double>>> embedBatch(
    List<String> texts, {
    void Function(int done, int total)? onProgress,
  }) async {
    const batchSize = 8;
    final results   = <List<double>>[];

    for (int i = 0; i < texts.length; i += batchSize) {
      final end   = (i + batchSize).clamp(0, texts.length);
      final batch = texts.sublist(i, end);

      for (final text in batch) {
        final vec = await embed(text);
        results.add(vec);
        await Future.delayed(const Duration(milliseconds: 120));
      }

      onProgress?.call(end, texts.length);
    }
    return results;
  }
}
