// lib/screens/sign_in_screen.dart
import 'package:flutter/material.dart';
import '../services/school_auth_service.dart';
import '../services/user_profile_sync.dart';
import '../theme/app_theme.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  var _busy = false;
  String? _error;

  Future<void> _onGoogleTap() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final cred = await SchoolAuthService.signInWithGoogle();
      final u = cred.user;
      if (u != null) await UserProfileSync.ensureForCurrentUser(u);
    } catch (e) {
      setState(() => _error = e.toString());
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
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              const Icon(Icons.school_rounded, size: 56, color: AppTheme.accent),
              const SizedBox(height: 20),
              const Text(
                'TLU AI Assistant',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 26,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Đăng nhập bằng Google trường\n(${SchoolAuthService.allowedEmailSuffix})',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 15,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Cần file Firebase cho Android/iOS (xem README hoặc hỏi team).',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textTertiary,
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppTheme.accentRed,
                    fontSize: 13,
                  ),
                ),
              ],
              const Spacer(),
              FilledButton.icon(
                onPressed: _busy ? null : _onGoogleTap,
                icon: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppTheme.background,
                        ),
                      )
                    : const Icon(Icons.login_rounded),
                label: Text(_busy ? 'Đang đăng nhập…' : 'Đăng nhập Google'),
                style: FilledButton.styleFrom(
                  backgroundColor: AppTheme.accent,
                  foregroundColor: AppTheme.background,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
