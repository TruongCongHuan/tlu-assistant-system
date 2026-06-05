// lib/models/document_chunk.dart

class DocumentChunk {
  final String id;
  final String docId;
  final String docName;
  final String text;
  final int pageNumber;
  final int chunkIndex;
  List<double> embedding;

  DocumentChunk({
    required this.id,
    required this.docId,
    required this.docName,
    required this.text,
    required this.pageNumber,
    required this.chunkIndex,
    this.embedding = const [],
  });

  Map<String, dynamic> toMap() => {
        'id': id,
        'doc_id': docId,
        'doc_name': docName,
        'text': text,
        'page_number': pageNumber,
        'chunk_index': chunkIndex,
        'embedding': embedding.join(','),
      };

  factory DocumentChunk.fromMap(Map<String, dynamic> m) => DocumentChunk(
        id: m['id'] as String,
        docId: m['doc_id'] as String,
        docName: m['doc_name'] as String,
        text: m['text'] as String,
        pageNumber: m['page_number'] as int,
        chunkIndex: m['chunk_index'] as int,
        embedding: (m['embedding'] as String)
            .split(',')
            .where((s) => s.isNotEmpty)
            .map(double.parse)
            .toList(),
      );
}
