// lib/models/conversation.dart

import 'rag_stream.dart';

enum MessageRole { user, assistant }
enum MessageStatus { sending, done, error }

class ChatMessage {
  final String id;
  final String text;
  final MessageRole role;
  final MessageStatus status;
  final DateTime createdAt;
  final List<String> sourcePages; // Trang tài liệu nguồn
  /// Câu hỏi sinh viên tương ứng (assistant message).
  final String? userQuestion;
  final List<RetrievedContextPreview> retrievedContexts;
  final RagMessageRating ragRating;
  final String? retrievalMode;

  const ChatMessage({
    required this.id,
    required this.text,
    required this.role,
    this.status = MessageStatus.done,
    required this.createdAt,
    this.sourcePages = const [],
    this.userQuestion,
    this.retrievedContexts = const [],
    this.ragRating = RagMessageRating.none,
    this.retrievalMode,
  });

  ChatMessage copyWith({
    String? text,
    MessageStatus? status,
    List<String>? sourcePages,
    String? userQuestion,
    List<RetrievedContextPreview>? retrievedContexts,
    RagMessageRating? ragRating,
    String? retrievalMode,
  }) =>
      ChatMessage(
        id: id,
        text: text ?? this.text,
        role: role,
        status: status ?? this.status,
        createdAt: createdAt,
        sourcePages: sourcePages ?? this.sourcePages,
        userQuestion: userQuestion ?? this.userQuestion,
        retrievedContexts: retrievedContexts ?? this.retrievedContexts,
        ragRating: ragRating ?? this.ragRating,
        retrievalMode: retrievalMode ?? this.retrievalMode,
      );

  bool get isUser => role == MessageRole.user;
  bool get isAI => role == MessageRole.assistant;
}

// ── Document metadata ─────────────────────────────
class PdfDoc {
  final String id;
  final String name;
  final String path;
  final int chunkCount;
  final DateTime indexedAt;

  const PdfDoc({
    required this.id,
    required this.name,
    required this.path,
    required this.chunkCount,
    required this.indexedAt,
  });
}
