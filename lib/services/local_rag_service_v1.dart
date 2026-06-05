// lib/services/local_rag_service_v1.dart
// PHIÊN BẢN CŨ (BACKUP) - Dùng để so sánh hiệu quả RAG
import 'dart:io';
import 'dart:isolate';
import 'package:flutter/foundation.dart';
import 'package:google_generative_ai/google_generative_ai.dart';
import 'package:uuid/uuid.dart';
import '../models/document_chunk.dart';
import 'pdf_service.dart';
import 'embedding_service.dart';
import 'vector_store.dart';

typedef ProgressCallback = void Function(String status, double progress);

class LocalRagServiceV1 {
  static const String _apiKey = 'AIzaSyBFuRQ4a5sbF5maaJ-gLH4JUGshCgbIAFs';
  static const String _llmModel = 'models/gemini-1.5-flash-latest';

  final _embedder = EmbeddingService();
  late final GenerativeModel _llm;

  LocalRagServiceV1() {
    _llm = GenerativeModel(
      model: _llmModel,
      apiKey: _apiKey,
      generationConfig: GenerationConfig(
        temperature: 0.3,
        maxOutputTokens: 1024,
      ),
      systemInstruction: Content.text(
        'Bạn là trợ lý học tập thông minh của sinh viên Đại học Thăng Long (TLU). '
        'Trả lời bằng tiếng Việt, rõ ràng và súc tích. '
        'Chỉ dựa vào nội dung tài liệu được cung cấp. '
        'Nếu tài liệu không có thông tin, hãy nói thẳng điều đó.',
      ),
    );
  }

  Future<void> indexPdf({
    required String filePath,
    ProgressCallback? onProgress,
  }) async {
    final file    = File(filePath);
    final docId   = const Uuid().v4();
    final docName = filePath.split('/').last;

    onProgress?.call('Đang đọc file MD…', 0.05);
    final pageTexts = await compute(_extractInIsolate, filePath);

    if (pageTexts.isEmpty) {
      throw Exception('Không thể đọc text từ file này.');
    }

    onProgress?.call('Đang chia nhỏ nội dung…', 0.15);
    final chunks = PdfService.chunk(
      docId: docId,
      docName: docName,
      pageTexts: pageTexts,
    );

    final texts  = chunks.map((c) => c.text).toList();
    final embeds = await _embedder.embedBatch(
      texts,
      onProgress: (done, total) {
        final p = 0.15 + (done / total * 0.75);
        onProgress?.call('Đang tạo vector ($done/$total)…', p);
      },
    );

    for (int i = 0; i < chunks.length; i++) {
      chunks[i].embedding = embeds[i];
    }

    onProgress?.call('Đang lưu vào bộ nhớ…', 0.92);
    await VectorStore.insertChunks(chunks);
    await VectorStore.insertDocument(
      id: docId,
      name: docName,
      path: filePath,
      chunkCount: chunks.length,
    );

    onProgress?.call('Hoàn tất!', 1.0);
  }

  Stream<String> queryStream(String question, {String? docId}) async* {
    // PHIÊN BẢN CŨ: Chỉ search 1 lần duy nhất, không mở rộng từ khóa
    final queryVec = await _embedder.embed(question);

    final results = await VectorStore.search(
      queryVec: queryVec,
      topK: 5,
      docId: docId,
    );

    if (results.isEmpty) {
      yield 'Không tìm thấy thông tin liên quan.';
      return;
    }

    final context = results.asMap().entries.map((e) {
      final r = e.value;
      return '[Đoạn ${e.key + 1}]\n${r.chunk.text}';
    }).join('\n\n---\n\n');

    final sourceInfo = results
        .map((r) => r.chunk.docName)
        .toSet()
        .join(', ');

    final prompt = '''
Dưới đây là nội dung từ tài liệu của sinh viên:
$context

Câu hỏi: $question

Hãy trả lời dựa trên nội dung tài liệu trên. 
Ở cuối câu trả lời, thêm dòng: "📚 Nguồn: $sourceInfo"
''';

    final stream = _llm.generateContentStream([Content.text(prompt)]);
    await for (final chunk in stream) {
      if (chunk.text != null && chunk.text!.isNotEmpty) {
        yield chunk.text!;
      }
    }
  }

  static Future<Map<int, String>> _extractInIsolate(String path) async {
    return PdfService.extractText(File(path));
  }
}
