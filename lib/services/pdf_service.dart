// lib/services/pdf_service.dart
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:uuid/uuid.dart';
import '../models/document_chunk.dart';

class PdfService {
  static const int _maxChunkSize = 1200; // Ngưỡng tối đa cho một chunk MD
  static const int _overlap      = 150;  // Chồng chéo giữa các tiểu đoạn

  // ── Chọn 1 hoặc nhiều tài liệu (.md, .txt) ────────────────────────────
  static Future<List<File>> pickPdfs({bool allowMultiple = true}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['md', 'txt'],
      allowMultiple: allowMultiple,
      withData: false,
    );
    if (result == null) return [];
    return result.files
        .where((f) => f.path != null)
        .map((f) => File(f.path!))
        .toList();
  }

  // ── Đọc nội dung file ───────────────────────────
  static Future<Map<int, String>> extractText(File file) async {
    final text = await file.readAsString();
    return {1: text}; // Coi như 1 block thô để chunking xử lý sau
  }

  // ── Chiến lược Semantic Markdown Chunking ───────────────────────────
  static List<DocumentChunk> chunk({
    required String docId,
    required String docName,
    required Map<int, String> pageTexts,
  }) {
    final uuid = const Uuid();
    final chunks = <DocumentChunk>[];
    int ci = 0;

    // Lấy nội dung gốc
    final fullText = pageTexts[1] ?? "";
    if (fullText.isEmpty) return [];

    // 1. Tách theo Header (## hoặc #)
    final sections = _splitByHeadings(fullText);

    for (var section in sections) {
      final heading = section['heading']!;
      final content = section['content']!;
      
      // Nếu section quá dài (VD: 3000 ký tự), chia nhỏ tiếp nhưng giữ header
      if (content.length > _maxChunkSize) {
        final subChunks = _splitSubSection(content, heading);
        for (var sub in subChunks) {
          chunks.add(_buildChunk(uuid, docId, docName, sub, 1, ci++));
        }
      } else {
        final combined = heading.isNotEmpty ? "$heading\n$content" : content;
        if (combined.trim().length > 20) {
          chunks.add(_buildChunk(uuid, docId, docName, combined, 1, ci++));
        }
      }
    }

    return chunks;
  }

  // Tách văn bản dựa trên Markdown Heading (##)
  static List<Map<String, String>> _splitByHeadings(String text) {
    final List<Map<String, String>> sections = [];
    final lines = text.split('\n');
    String currentHeading = "";
    StringBuffer currentContent = StringBuffer();

    for (var line in lines) {
      if (line.trim().startsWith('##')) {
        // Lưu section cũ nếu có
        if (currentContent.isNotEmpty || currentHeading.isNotEmpty) {
          sections.add({
            'heading': currentHeading,
            'content': currentContent.toString().trim(),
          });
        }
        currentHeading = line.trim();
        currentContent = StringBuffer();
      } else {
        currentContent.writeln(line);
      }
    }
    
    // Lưu section cuối
    if (currentContent.isNotEmpty || currentHeading.isNotEmpty) {
      sections.add({
        'heading': currentHeading,
        'content': currentContent.toString().trim(),
      });
    }
    
    return sections;
  }

  // Chia nhỏ một section quá dài nhưng cố gắng giữ nguyên bảng biểu/danh sách
  static List<String> _splitSubSection(String content, String heading) {
    final List<String> subChunks = [];
    final lines = content.split('\n');
    StringBuffer buffer = StringBuffer();
    bool isInTable = false;

    for (var line in lines) {
      final isTableLine = line.trim().startsWith('|');
      
      // Nếu dòng hiện tại làm buffer quá dài, và CHƯA đang ở trong một bảng, hoặc đây là điểm kết thúc bảng
      if (buffer.length + line.length > _maxChunkSize && (!isTableLine || !isInTable)) {
        subChunks.add("${heading.isNotEmpty ? '$heading (Tiếp theo)\n' : ''}${buffer.toString().trim()}");
        
        // Giữ lại overlap ngữ cảnh
        final previousLines = buffer.toString().trim().split('\n');
        final overlap = previousLines.length > 3 
            ? previousLines.sublist(previousLines.length - 3).join('\n') 
            : "";
        
        buffer = StringBuffer();
        if (overlap.isNotEmpty) buffer.writeln(overlap);
      }
      
      buffer.writeln(line);
      isInTable = isTableLine;
    }

    if (buffer.isNotEmpty) {
      subChunks.add("${heading.isNotEmpty ? '$heading (Tiếp theo)\n' : ''}${buffer.toString().trim()}");
    }

    return subChunks;
  }

  static DocumentChunk _buildChunk(Uuid uuid, String docId, String docName, String text, int page, int index) {
    return DocumentChunk(
      id: uuid.v4(),
      docId: docId,
      docName: docName,
      text: text,
      pageNumber: page,
      chunkIndex: index,
    );
  }

  static String _clean(String raw) => raw.trim();
}
