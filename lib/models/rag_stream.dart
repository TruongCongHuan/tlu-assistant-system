/// SSE events from `POST /v1/chat/stream`.
class RetrievedContextPreview {
  final String? chunkId;
  final String? docName;
  final double? score;
  final String preview;

  const RetrievedContextPreview({
    this.chunkId,
    this.docName,
    this.score,
    this.preview = '',
  });

  factory RetrievedContextPreview.fromJson(Map<String, dynamic> json) {
    return RetrievedContextPreview(
      chunkId: json['chunk_id'] as String?,
      docName: json['doc_name'] as String?,
      score: (json['score'] as num?)?.toDouble(),
      preview: json['preview'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        if (chunkId != null) 'chunk_id': chunkId,
        if (docName != null) 'doc_name': docName,
        if (score != null) 'score': score,
        'preview': preview,
      };
}

class RagStreamMeta {
  final String sources;
  final String retrievalMode;
  final List<RetrievedContextPreview> contexts;

  const RagStreamMeta({
    this.sources = '',
    this.retrievalMode = 'dense',
    this.contexts = const [],
  });

  factory RagStreamMeta.fromJson(Map<String, dynamic> json) {
    final raw = json['retrieved_contexts'];
    final list = raw is List
        ? raw
            .whereType<Map>()
            .map((e) => RetrievedContextPreview.fromJson(
                  Map<String, dynamic>.from(e),
                ))
            .toList()
        : <RetrievedContextPreview>[];
    return RagStreamMeta(
      sources: json['sources'] as String? ?? '',
      retrievalMode: json['retrieval_mode'] as String? ?? 'dense',
      contexts: list,
    );
  }
}

enum RagStreamEventKind { meta, text, error, done }

class RagStreamEvent {
  final RagStreamEventKind kind;
  final String? text;
  final RagStreamMeta? meta;

  const RagStreamEvent._(this.kind, {this.text, this.meta});

  const RagStreamEvent.meta(RagStreamMeta meta)
      : this._(RagStreamEventKind.meta, meta: meta);

  const RagStreamEvent.text(String text)
      : this._(RagStreamEventKind.text, text: text);

  const RagStreamEvent.error(String text)
      : this._(RagStreamEventKind.error, text: text);

  const RagStreamEvent.done() : this._(RagStreamEventKind.done);
}

enum RagMessageRating { none, up, down }
