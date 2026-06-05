// lib/screens/feedback_letter_screen.dart
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import '../config/app_runtime_config.dart';
import '../services/local_feedback_service.dart';
import '../theme/app_theme.dart';
import '../widgets/notification_bell_button.dart';
import 'application_form_screen.dart';

/// Góp ý — có tuỳ chọn ẩn danh: vẫn gửi nội dung nhưng không bắt buộc khai danh tính công khai.
class FeedbackLetterScreen extends StatefulWidget {
  const FeedbackLetterScreen({super.key});

  @override
  State<FeedbackLetterScreen> createState() => _FeedbackLetterScreenState();
}

class _FeedbackLetterScreenState extends State<FeedbackLetterScreen> {
  final _subjectCtrl = TextEditingController();
  final _bodyCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  var _anonymous = false;
  var _sending = false;

  @override
  void dispose() {
    _subjectCtrl.dispose();
    _bodyCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final subject = _subjectCtrl.text.trim();
    final body = _bodyCtrl.text.trim();
    if (subject.isEmpty || body.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vui lòng nhập tiêu đề và nội dung thư.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }
    if (!_anonymous && _nameCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Tắt ẩn danh thì vui lòng nhập họ tên / MSSV (hoặc bật ẩn danh).'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }
    setState(() => _sending = true);
    try {
      if (AppRuntimeConfig.useLocalApi) {
        await LocalFeedbackService.submit(
          subject: subject,
          body: body,
          anonymous: _anonymous,
          studentLabel: _anonymous ? null : _nameCtrl.text.trim(),
        );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Đã gửi góp ý. Cảm ơn bạn!'),
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
            content: Text('Vui lòng đăng nhập để gửi thư.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }

      await FirebaseFirestore.instance.collection('feedback_letters').add({
        'subject': subject,
        'body': body,
        'anonymous': _anonymous,
        'studentLabel': _anonymous ? null : _nameCtrl.text.trim(),
        'source': 'tlu_ai_app',
        'studentUid': user.uid,
        'studentEmail': user.email ?? '',
        'createdAt': FieldValue.serverTimestamp(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã gửi thư góp ý.'),
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
        title: const Text('Gửi thư góp ý'),
        actions: const [NotificationBellButton()],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.surfaceHigh,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.surfaceBorder),
            ),
            child: const Text(
              'Ẩn danh: bạn không cần điền họ tên; phía nhà trường vẫn nhận nội dung '
              '(tuỳ chính sách lưu trữ / xử lý). Nên bật khi phản ánh nhạy cảm.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.4),
            ),
          ),
          const SizedBox(height: 16),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text(
              'Gửi ẩn danh',
              style: TextStyle(color: AppTheme.textPrimary),
            ),
            subtitle: const Text(
              'Không gửi kèm họ tên / MSSV',
              style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
            ),
            value: _anonymous,
            onChanged: (v) => setState(() => _anonymous = v),
          ),
          if (!_anonymous) ...[
            const SizedBox(height: 8),
            const Text(
              'Họ tên / MSSV',
              style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _nameCtrl,
              style: const TextStyle(color: AppTheme.textPrimary),
              decoration: ApplicationFormScreen.outlineDecoration(
                  hint: 'Nguyễn Văn A — 1022xxxx'),
            ),
          ],
          const SizedBox(height: 20),
          const Text(
            'Tiêu đề',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _subjectCtrl,
            style: const TextStyle(color: AppTheme.textPrimary),
            decoration: ApplicationFormScreen.outlineDecoration(hint: 'Tiêu đề ngắn gọn'),
          ),
          const SizedBox(height: 20),
          const Text(
            'Nội dung',
            style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _bodyCtrl,
            minLines: 6,
            maxLines: 14,
            style: const TextStyle(color: AppTheme.textPrimary),
            decoration: ApplicationFormScreen.outlineDecoration(hint: 'Nội dung góp ý…'),
          ),
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
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Gửi thư'),
          ),
        ],
      ),
    );
  }
}
