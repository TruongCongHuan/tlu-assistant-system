// lib/screens/pdf_manager_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../services/pdf_service.dart';
import '../services/local_rag_service.dart';
import '../services/vector_store.dart';
import '../providers/chat_provider.dart';
import '../widgets/notification_bell_button.dart';

class PdfManagerScreen extends StatefulWidget {
  const PdfManagerScreen({super.key});

  @override
  State<PdfManagerScreen> createState() => _PdfManagerScreenState();
}

class _PdfManagerScreenState extends State<PdfManagerScreen> {
  final _rag = LocalRagService();

  List<Map<String, dynamic>> _docs      = [];
  bool                        _indexing  = false;
  String                      _status    = '';
  double                      _progress  = 0;

  @override
  void initState() {
    super.initState();
    _loadDocs();
  }

  Future<void> _loadDocs() async {
    final docs = await VectorStore.getDocuments();
    if (mounted) setState(() => _docs = docs);
  }

  Future<void> _pickAndIndex() async {
    final files = await PdfService.pickPdfs(allowMultiple: true);
    if (files.isEmpty) return;

    for (final file in files) {
      if (!mounted) return;
      setState(() {
        _indexing  = true;
        _status    = 'Bắt đầu xử lý ${file.path.split('/').last}…';
        _progress  = 0;
      });

      try {
        await _rag.indexPdf(
          filePath: file.path,
          onProgress: (status, progress) {
            if (mounted) setState(() {
              _status   = status;
              _progress = progress;
            });
          },
        );
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Lỗi: ${e.toString()}'),
              backgroundColor: AppTheme.accentRed,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    }

    setState(() {
      _indexing = false;
      _status   = '';
      _progress = 0;
    });
    await _loadDocs();
  }

  Future<void> _deleteDoc(String docId, String docName) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppTheme.surfaceHigh,
        title: const Text('Xóa tài liệu',
            style: TextStyle(color: AppTheme.textPrimary)),
        content: Text('Xóa "$docName"?\nCác vector sẽ bị xóa vĩnh viễn.',
            style: const TextStyle(color: AppTheme.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.accentRed),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    await VectorStore.deleteDocument(docId);
    await _loadDocs();
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: const Text('Tài liệu'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_rounded, color: AppTheme.textPrimary),
            tooltip: 'Thêm tài liệu (.md, .txt)',
            onPressed: _indexing ? null : _pickAndIndex,
          ),
          const NotificationBellButton(),
        ],
      ),
      body: Column(
        children: [
          // ── Indexing Progress ──────────────────────
          if (_indexing)
            _IndexingCard(status: _status, progress: _progress)
                .animate()
                .fadeIn()
                .slideY(begin: -0.2, end: 0),

          // ── Docs List ─────────────────────────────
          Expanded(
            child: _docs.isEmpty && !_indexing
                ? _EmptyDocs(onAdd: _pickAndIndex)
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _docs.length,
                    separatorBuilder: (_, __) =>
                        const Divider(color: AppTheme.surfaceBorder),
                    itemBuilder: (_, i) {
                      final doc      = _docs[i];
                      final isActive = chat.activeDocId == doc['id'];
                      return _DocTile(
                        doc: doc,
                        isActive: isActive,
                        onTap: () {
                          chat.setActiveDoc(isActive ? null : doc['id'] as String);
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(isActive
                                  ? 'Đã bỏ chọn tài liệu'
                                  : 'Đang tìm kiếm trong: ${doc['name']}'),
                              behavior: SnackBarBehavior.floating,
                              duration: const Duration(seconds: 2),
                            ),
                          );
                        },
                        onDelete: () =>
                            _deleteDoc(doc['id'] as String, doc['name'] as String),
                      ).animate().fadeIn(
                            delay: Duration(milliseconds: i * 60),
                          );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ── Indexing progress card ─────────────────────────────
class _IndexingCard extends StatelessWidget {
  final String status;
  final double progress;

  const _IndexingCard({required this.status, required this.progress});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.accent.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  value: progress == 0 ? null : progress,
                  strokeWidth: 2,
                  color: AppTheme.accent,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  status,
                  style: const TextStyle(
                      color: AppTheme.textPrimary, fontSize: 13),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${(progress * 100).toInt()}%',
                style: const TextStyle(
                    color: AppTheme.accent, fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: progress == 0 ? null : progress,
            backgroundColor: AppTheme.surfaceHigh,
            valueColor: const AlwaysStoppedAnimation(AppTheme.accent),
            borderRadius: BorderRadius.circular(4),
            minHeight: 4,
          ),
        ],
      ),
    );
  }
}

// ── Single doc tile ────────────────────────────────────
class _DocTile extends StatelessWidget {
  final Map<String, dynamic> doc;
  final bool isActive;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _DocTile({
    required this.doc,
    required this.isActive,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final name   = doc['name'] as String;
    final chunks = doc['chunk_count'] as int;
    final ts     = doc['indexed_at'] as int;
    final date   = DateTime.fromMillisecondsSinceEpoch(ts);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          children: [
            // PDF icon
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: isActive
                    ? AppTheme.accent.withOpacity(0.15)
                    : AppTheme.surfaceHigh,
                borderRadius: BorderRadius.circular(10),
                border: isActive
                    ? Border.all(color: AppTheme.accent.withOpacity(0.4))
                    : null,
              ),
              child: Icon(
                Icons.description_rounded,
                color: isActive ? AppTheme.accent : AppTheme.textSecondary,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),

            // Name + info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: TextStyle(
                      color: isActive ? AppTheme.accent : AppTheme.textPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '$chunks đoạn · ${date.day}/${date.month}/${date.year}',
                    style: const TextStyle(
                        color: AppTheme.textTertiary, fontSize: 12),
                  ),
                ],
              ),
            ),

            // Active check
            if (isActive)
              const Icon(Icons.check_circle_rounded,
                  color: AppTheme.accent, size: 18),

            // Delete
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded,
                  color: AppTheme.textTertiary, size: 20),
              onPressed: onDelete,
              padding: const EdgeInsets.all(8),
              constraints: const BoxConstraints(),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyDocs extends StatelessWidget {
  final VoidCallback onAdd;
  const _EmptyDocs({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.upload_file_rounded,
              size: 64, color: AppTheme.textTertiary),
          const SizedBox(height: 16),
          const Text('Chưa có tài liệu nào',
              style:
                  TextStyle(color: AppTheme.textSecondary, fontSize: 16)),
          const SizedBox(height: 8),
          const Text('Thêm tài liệu (.md, .txt) để bắt đầu học cùng TLU AI',
              style:
                  TextStyle(color: AppTheme.textTertiary, fontSize: 13)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: onAdd,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Thêm tài liệu'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accent,
              foregroundColor: AppTheme.background,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24)),
            ),
          ),
        ],
      ),
    );
  }
}
