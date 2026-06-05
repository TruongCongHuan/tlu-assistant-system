// lib/widgets/firebase_auth_gate.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../services/firebase_session_service.dart';
import '../services/push_notification_service.dart';
import '../services/user_profile_sync.dart';
import '../theme/app_theme.dart';

/// Tạm thời: không bắt Google — dùng Firebase **Anonymous** + FCM.
/// Chưa init Firebase → màn hướng dẫn. Đã init → luôn có phiên (ẩn danh).
class FirebaseAuthGate {
  FirebaseAuthGate._();

  /// `true` = bỏ qua màn chờ auth (phiên vẫn được tạo trong [main] qua Anonymous).
  static const bool kBypassAuthGate = true;

  static Widget wrap(Widget? child) {
    if (child == null) {
      return const SizedBox.shrink();
    }
    if (DemoReportConfig.enabled ||
        AppRuntimeConfig.useLocalApi ||
        kBypassAuthGate) {
      return child;
    }
    if (Firebase.apps.isEmpty) {
      return const _FirebaseRequiredScreen();
    }
    return _AuthListener(child: child);
  }
}

class _FirebaseRequiredScreen extends StatelessWidget {
  const _FirebaseRequiredScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(height: 32),
              Icon(Icons.cloud_off_outlined, size: 56, color: AppTheme.accent),
              SizedBox(height: 20),
              Text(
                'Chưa kết nối Firebase',
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                ),
              ),
              SizedBox(height: 12),
              Text(
                'Android: android/app/google-services.json + plugin com.google.gms.google-services '
                '(ở cuối app/build.gradle), rồi flutter clean && flutter run.',
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 14,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuthListener extends StatelessWidget {
  final Widget child;

  const _AuthListener({required this.child});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            backgroundColor: AppTheme.background,
            body: Center(
              child: CircularProgressIndicator(color: AppTheme.accent),
            ),
          );
        }
        if (snapshot.data == null) {
          return const _AnonymousBootstrapScreen();
        }
        return child;
      },
    );
  }
}

class _AnonymousBootstrapScreen extends StatefulWidget {
  const _AnonymousBootstrapScreen();

  @override
  State<_AnonymousBootstrapScreen> createState() => _AnonymousBootstrapScreenState();
}

class _AnonymousBootstrapScreenState extends State<_AnonymousBootstrapScreen> {
  String? _err;
  var _busy = true;

  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final u = await FirebaseSessionService.ensureSignedIn();
      if (u != null) {
        await UserProfileSync.ensureForCurrentUser(u);
        await PushNotificationService.init();
      }
    } catch (e) {
      setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (_busy) ...[
                const CircularProgressIndicator(color: AppTheme.accent),
                const SizedBox(height: 16),
                const Text(
                  'Đang vào phiên…',
                  style: TextStyle(color: AppTheme.textSecondary),
                ),
              ] else if (_err != null) ...[
                Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.redAccent)),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: _go,
                  child: const Text('Thử lại'),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Bật Anonymous trong Firebase Console → Authentication → Sign-in method.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppTheme.textTertiary, fontSize: 12),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
