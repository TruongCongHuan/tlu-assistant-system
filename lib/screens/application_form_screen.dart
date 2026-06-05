// lib/screens/application_form_screen.dart
import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import '../config/app_runtime_config.dart';
import '../services/local_submission_service.dart';
import '../theme/app_theme.dart';
import '../widgets/notification_bell_button.dart';

class ApplicationFormScreen extends StatefulWidget {
  const ApplicationFormScreen({super.key});

  static InputDecoration outlineDecoration({required String hint}) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: AppTheme.textTertiary),
      filled: true,
      fillColor: AppTheme.surfaceHigh,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppTheme.surfaceBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppTheme.surfaceBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppTheme.accent),
      ),
    );
  }

  @override
  State<ApplicationFormScreen> createState() => _ApplicationFormScreenState();
}

class _ApplicationFormScreenState extends State<ApplicationFormScreen> {
  static const _uuid = Uuid();
  static const _maxFiles = 5;
  static const _maxBytesPerFile = 12 * 1024 * 1024; // 12 MB

  final _titleCtrl = TextEditingController();
  final _detailsCtrl = TextEditingController();
  final List<PlatformFile> _attachments = [];
  var _sending = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _detailsCtrl.dispose();
    super.dispose();
  }

  String? _mimeForFileName(String name) {
    final lower = name.toLowerCase();
    if (lower.endsWith('.pdf')) return 'application/pdf';
    if (lower.endsWith('.doc')) return 'application/msword';
    if (lower.endsWith('.docx')) {
      return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    }
    return null;
  }

  Future<void> _pickAttachments() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'doc', 'docx'],
      allowMultiple: true,
      withData: kIsWeb,
    );
    if (result == null || result.files.isEmpty) return;

    final merged = [..._attachments, ...result.files];
    if (merged.length > _maxFiles) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Chỉ được đính kèm tối đa 5 tệp.'),
            behavior: SnackBarBehavior.floating,
            backgroundColor: AppTheme.accentRed,
          ),
        );
      }
      return;
    }

    for (final f in result.files) {
      if (f.size > _maxBytesPerFile) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Tệp "${f.name}" vượt quá 12 MB.'),
              behavior: SnackBarBehavior.floating,
              backgroundColor: AppTheme.accentRed,
            ),
          );
        }
        return;
      }
    }

    setState(() {
      _attachments.clear();
      _attachments.addAll(merged.take(_maxFiles));
    });
  }

  void _removeAttachment(int index) {
    setState(() => _attachments.removeAt(index));
  }

  Future<List<Map<String, dynamic>>> _uploadAttachments(String batchId) async {
    final bucket = FirebaseStorage.instance;
    final out = <Map<String, dynamic>>[];

    for (var i = 0; i < _attachments.length; i++) {
      final f = _attachments[i];
      final safeBase =
          f.name.replaceAll(RegExp(r'[^\w.\-]'), '_').replaceAll('..', '_');
      final objectPath =
          'application_submissions/$batchId/${i}_$safeBase';
      final ref = bucket.ref(objectPath);
      final mime = _mimeForFileName(f.name) ?? 'application/octet-stream';
      final meta = SettableMetadata(contentType: mime);

      if (kIsWeb) {
        if (f.bytes == null) {
          throw StateError('Không đọc được dữ liệu tệp: ${f.name}');
        }
        await ref.putData(f.bytes!, meta);
      } else {
        if (f.path != null) {
          await ref.putFile(File(f.path!), meta);
        } else if (f.bytes != null) {
          await ref.putData(f.bytes!, meta);
        } else {
          throw StateError('Không đọc được tệp: ${f.name}');
        }
      }

      final url = await ref.getDownloadURL();
      out.add({
        'name': f.name,
        'url': url,
        'size': f.size,
        'storagePath': objectPath,
      });
    }
    return out;
  }

  Future<void> _submit() async {
    final title = _titleCtrl.text.trim();
    final details = _detailsCtrl.text.trim();
    if (title.isEmpty || details.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vui lòng nhập tiêu đề và nội dung.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }
    setState(() => _sending = true);
    try {
      if (AppRuntimeConfig.useLocalApi) {
        final files = <http.MultipartFile>[];
        for (var i = 0; i < _attachments.length; i++) {
          final f = _attachments[i];
          if (f.bytes != null) {
            files.add(http.MultipartFile.fromBytes(
              'files',
              f.bytes!,
              filename: f.name,
            ));
          } else if (f.path != null) {
            files.add(await http.MultipartFile.fromPath(
              'files',
              f.path!,
              filename: f.name,
            ));
          }
        }
        await LocalSubmissionService.submit(
          title: title,
          details: details,
          files: files,
        );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Đã gửi đơn từ.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        Navigator.pop(context);
        return;
      }

      // PRODUCTION_FIREBASE
      if (Firebase.apps.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Chưa cấu hình Firebase — không thể gửi.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Vui lòng đăng nhập để gửi đơn.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }

      final batchId = _uuid.v4();
      List<Map<String, dynamic>> attachmentMeta = [];
      if (_attachments.isNotEmpty) {
        attachmentMeta = await _uploadAttachments(batchId);
      }

      await FirebaseFirestore.instance.collection('application_submissions').add({
        'title': title,
        'details': details,
        'source': 'tlu_ai_app',
        'uploadBatchId': batchId,
        'attachments': attachmentMeta,
        'studentUid': user.uid,
        'studentEmail': user.email ?? '',
        'createdAt': FieldValue.serverTimestamp(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã gửi đơn từ.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Lỗi: $e'),
          behavior: SnackBarBehavior.floating,
          backgroundColor: AppTheme.accentRed,
        ),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: const Text('Gửi đơn từ'),
        actions: const [NotificationBellButton()],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Tiêu đề đơn / loại đơn',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _titleCtrl,
            style: const TextStyle(color: AppTheme.textPrimary),
            decoration: ApplicationFormScreen.outlineDecoration(
                hint: 'Ví dụ: Đơn xin xác nhận điểm'),
          ),
          const SizedBox(height: 20),
          const Text(
            'Nội dung chi tiết',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _detailsCtrl,
            minLines: 6,
            maxLines: 14,
            style: const TextStyle(color: AppTheme.textPrimary),
            decoration: ApplicationFormScreen.outlineDecoration(
                hint: 'Mô tả lý do, thông tin cần xử lý…'),
          ),
          const SizedBox(height: 20),
          const Text(
            'Đính kèm (PDF, Word)',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 4),
          const Text(
            'Tối đa $_maxFiles tệp — .pdf, .doc, .docx — mỗi tệp ≤ 12 MB.',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 11, height: 1.35),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: _sending ? null : _pickAttachments,
            icon: const Icon(Icons.attach_file_rounded, size: 20),
            label: const Text('Chọn tệp PDF / Word'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.textPrimary,
              side: const BorderSide(color: AppTheme.surfaceBorder),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          if (_attachments.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(_attachments.length, (i) {
                final f = _attachments[i];
                return InputChip(
                  label: Text(
                    f.name,
                    style: const TextStyle(fontSize: 13),
                    overflow: TextOverflow.ellipsis,
                  ),
                  deleteIconColor: AppTheme.textSecondary,
                  onDeleted: _sending ? null : () => _removeAttachment(i),
                  backgroundColor: AppTheme.surfaceHigh,
                  side: const BorderSide(color: AppTheme.surfaceBorder),
                );
              }),
            ),
          ],
          const SizedBox(height: 28),
          FilledButton(
            onPressed: _sending ? null : _submit,
            style: FilledButton.styleFrom(
              backgroundColor: AppTheme.accent,
              foregroundColor: AppTheme.background,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: _sending
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppTheme.background,
                    ),
                  )
                : const Text('Gửi đơn'),
          ),
        ],
      ),
    );
  }
}
