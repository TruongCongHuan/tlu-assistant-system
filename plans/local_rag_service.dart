// lib/services/local_rag_service.dart
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

class LocalRagService {
  static const String _apiKey = 'AIzaSyBFuRQ4a5sbF5maaJ-gLH4JUGshCgbIAFs';
  static const String _llmModel = 'models/gemini-flash-latest';

  final _embedder = EmbeddingService();
  late final GenerativeModel _llm;

  LocalRagService() {
    _llm = GenerativeModel(
      model: _llmModel,
      apiKey: _apiKey,
      generationConfig: GenerationConfig(
        temperature: 0.5, 
        maxOutputTokens: 2048,
      ),
      systemInstruction: Content.text(
        'Bạn là Chuyên gia Tư vấn Học vụ AI của Đại học Thăng Long (TLU). '
        'QUY TRÌNH XỬ LÝ CÂU HỎI:\n'
        'BƯỚC 1 - Phân tích & Định danh: Xác định mục tiêu câu hỏi. Kiểm tra xem quy định có phụ thuộc vào Khóa học (K) hay Ngành học không. Nếu tài liệu chia theo đối tượng mà bạn chưa biết đối tượng của User, hãy hỏi khéo léo để xác định.\n'
        'BƯỚC 2 - Kiểm tra Hiệu lực: Nếu thấy nhiều văn bản trùng lặp, hãy ưu tiên văn bản có ngày ban hành mới nhất (năm học 2025-2026). Nêu rõ sự thay đổi nếu có (Ví dụ: "Từ năm nay, quy định X đã thay thế cho Y").\n'
        'BƯỚC 3 - Suy luận Logic: Kết nối các mốc thời gian (Lịch thi, lịch học) để đưa ra dự đoán thông minh nếu tài liệu không ghi trực tiếp ngày nghỉ/hạn chót.\n'
        'BƯỚC 4 - Tổng hợp & Phản hồi: Trả lời ngắn gọn, trực diện (giống phong cách Gemini Web). Tránh lan man. Sử dụng định dạng danh sách (bullet points) cho rõ ràng.\n'
        'BƯỚC 5 - Điều phối (Escalation): Nếu thông tin không có trong tài liệu hoặc câu hỏi quá phức tạp/nhạy cảm, hãy gợi ý: "Bạn có muốn tôi gửi câu hỏi này đến Cố vấn học tập (nếu về học tập/môn học) hoặc Cán bộ phòng Công tác sinh viên (nếu về chính sách/đời sống) không?"\n\n'
        'VÍ DỤ MẪU:\n'
        '- User: "Hạn nộp học phí?" -> AI: "Theo thông báo mới nhất ngày..., hạn là... Bạn lưu ý đóng đúng hạn để tránh bị khóa portal. Nếu cần hỗ trợ tài chính, bạn muốn tôi gửi câu hỏi đến phòng Tài chính không?"\n'
        '- User: "Môn IT học gì?" -> AI: "Ngành CNTT gồm các môn cốt lõi: Cấu trúc dữ liệu, Thuật toán, Web... (liệt kê bảng). Bạn thuộc K37 hay K38 để mình gửi đúng khung chương trình?"\n\n'
        'LƯU Ý: Tuyệt đối không bịa đặt thông tin. Luôn giữ thái độ chuyên nghiệp, tận tâm.',
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

    onProgress?.call('Hoàn tất! ${chunks.length} đoạn văn đã được index.', 1.0);
  }

  Stream<String> queryStream(String question, {String? docId}) async* {
    final searchQueries = await _expandQuery(question);
    
    final allResults = <({DocumentChunk chunk, double score})>[];
    for (var q in searchQueries) {
      final vec = await _embedder.embed(q);
      final res = await VectorStore.search(
        queryVec: vec,
        topK: 5, 
        docId: docId,
      );
      allResults.addAll(res);
    }

    final seen = <String>{};
    final uniqueResults = allResults.where((r) {
      if (seen.contains(r.chunk.text)) return false;
      seen.add(r.chunk.text);
      return true;
    }).toList();

    if (uniqueResults.isEmpty) {
      yield 'Không tìm thấy thông tin liên quan trong tài liệu. Hãy thử đặt câu hỏi khác hoặc nạp tài liệu mới nhất.';
      return;
    }

    final context = uniqueResults.take(12).toList().asMap().entries.map((e) {
      final r = e.value;
      return '[Đoạn ${e.key + 1} - ${r.chunk.docName}]\n${r.chunk.text}';
    }).join('\n\n---\n\n');

    final sourceInfo = uniqueResults.take(3).map((r) => r.chunk.docName).toSet().join(', ');

    final now = DateTime.now();
    final prompt = '''
Hôm nay: ${now.day}/${now.month}/${now.year}. 

Dữ liệu Sổ tay sinh viên:
---
$context
---

Câu hỏi: "$question"

Thực hiện phản hồi theo các nguyên tắc:
1. Trả lời súc tích, đi thẳng vào vấn đề. Ưu tiên các bảng biểu và mốc thời gian của năm học 2025-2026.
2. Nếu câu hỏi về môn học/chương trình đào tạo, hãy trình bày rõ ràng danh sách môn học tìm được. 
3. Nếu thông tin có sự phân hóa theo đối tượng (K, Ngành), hãy chỉ rõ điều đó và hỏi thêm User nếu cần.
4. Nếu cảm thấy thông tin trong tài liệu không đủ hoặc không chắc chắn, hãy thực hiện Bước 5 trong Quy trình (Escalation).
5. Ghi nguồn: "📚 Nguồn: $sourceInfo"
''';

    final stream = _llm.generateContentStream([Content.text(prompt)]);
    await for (final chunk in stream) {
      if (chunk.text != null && chunk.text!.isNotEmpty) {
        yield chunk.text!;
      }
    }
  }

  Future<List<String>> _expandQuery(String question) async {
    try {
      final prompt = '''
Bạn là chuyên gia tra cứu. Với câu hỏi: "$question", hãy đưa ra 3-4 từ khóa tìm kiếm hiệu quả trong Sổ tay sinh viên. 
LƯU Ý VỀ CÁC TỪ VIẾT TẮT, ví dụ: IT = Công nghệ thông tin, SV = Sinh viên, HK = Học kỳ, HP = Học phần.
Chỉ trả về các cụm từ cách nhau bởi dấu phẩy.
Ví dụ: "ngành IT học gì" -> "Chương trình đào tạo Công nghệ thông tin, môn học IT, khung đào tạo Công nghệ thông tin"
''';
      final response = await _llm.generateContent([Content.text(prompt)]);
      final text = response.text ?? question;
      return text.split(',').map((s) => s.trim()).toList()..add(question);
    } catch (_) {
      return [question];
    }
  }

  static Future<Map<int, String>> _extractInIsolate(String path) async {
    return PdfService.extractText(File(path));
  }
}
