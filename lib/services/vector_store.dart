// lib/services/vector_store.dart
import 'dart:math';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import '../models/document_chunk.dart';

class VectorStore {
  static Database? _db;

  static Future<Database> get _database async {
    _db ??= await _init();
    return _db!;
  }

  static Future<Database> _init() async {
    final dbPath = await getDatabasesPath();
    return openDatabase(
      join(dbPath, 'tlu_rag_v1.db'),
      version: 1,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE chunks (
            id          TEXT PRIMARY KEY,
            doc_id      TEXT NOT NULL,
            doc_name    TEXT NOT NULL,
            text        TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            embedding   TEXT NOT NULL
          )
        ''');
        await db.execute('CREATE INDEX idx_doc ON chunks(doc_id)');

        // Metadata table
        await db.execute('''
          CREATE TABLE documents (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            path         TEXT NOT NULL,
            chunk_count  INTEGER NOT NULL DEFAULT 0,
            indexed_at   INTEGER NOT NULL
          )
        ''');
      },
    );
  }

  // ── Insert chunks sau khi embed ───────────────────────
  static Future<void> insertChunks(List<DocumentChunk> chunks) async {
    final db    = await _database;
    final batch = db.batch();
    for (final c in chunks) {
      batch.insert('chunks', c.toMap(),
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  // ── Lưu metadata document ────────────────────────────
  static Future<void> insertDocument({
    required String id,
    required String name,
    required String path,
    required int chunkCount,
  }) async {
    final db = await _database;
    await db.insert(
      'documents',
      {
        'id': id,
        'name': name,
        'path': path,
        'chunk_count': chunkCount,
        'indexed_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  // ── Top-K similarity search ──────────────────────────
  static Future<List<({DocumentChunk chunk, double score})>> search({
    required List<double> queryVec,
    int topK = 5,
    String? docId, // null = tìm tất cả docs
  }) async {
    final db   = await _database;
    final rows = await db.query(
      'chunks',
      where: docId != null ? 'doc_id = ?' : null,
      whereArgs: docId != null ? [docId] : null,
    );

    if (rows.isEmpty) return [];

    final scored = rows
        .map((r) {
          final c     = DocumentChunk.fromMap(r);
          final score = _cosine(queryVec, c.embedding);
          return (chunk: c, score: score);
        })
        .toList()
      ..sort((a, b) => b.score.compareTo(a.score));

    return scored.take(topK).toList();
  }

  // ── List all indexed documents ────────────────────────
  static Future<List<Map<String, dynamic>>> getDocuments() async {
    final db = await _database;
    return db.query('documents', orderBy: 'indexed_at DESC');
  }

  // ── Delete a document + its chunks ───────────────────
  static Future<void> deleteDocument(String docId) async {
    final db = await _database;
    await db.delete('chunks', where: 'doc_id = ?', whereArgs: [docId]);
    await db.delete('documents', where: 'id = ?', whereArgs: [docId]);
  }

  // ── Cosine similarity ─────────────────────────────────
  static double _cosine(List<double> a, List<double> b) {
    if (a.isEmpty || b.isEmpty || a.length != b.length) return 0;
    double dot = 0, na = 0, nb = 0;
    for (int i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      na  += a[i] * a[i];
      nb  += b[i] * b[i];
    }
    final denom = sqrt(na) * sqrt(nb);
    return denom == 0 ? 0 : dot / denom;
  }
}
