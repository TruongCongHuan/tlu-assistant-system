// lib/services/school_auth_service.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// Đăng nhập Google (tạm không dùng UI) + đăng xuất.
class SchoolAuthService {
  SchoolAuthService._();

  static const allowedEmailSuffix = '@thanglong.edu.vn';

  static GoogleSignIn? _googleClient;

  static String? _serverClientId() {
    const id = String.fromEnvironment('GOOGLE_OAUTH_CLIENT_ID', defaultValue: '');
    return id.isEmpty ? null : id;
  }

  static GoogleSignIn _googleSignIn() {
    _googleClient ??= GoogleSignIn(
      scopes: const <String>['email', 'profile'],
      serverClientId: _serverClientId(),
    );
    return _googleClient!;
  }

  static bool isAllowedSchoolEmail(String? email) {
    if (email == null) return false;
    return email.toLowerCase().trim().endsWith(allowedEmailSuffix);
  }

  static Future<UserCredential> signInWithGoogle() async {
    final google = _googleSignIn();
    final account = await google.signIn();
    if (account == null) {
      throw StateError('Đăng nhập bị hủy.');
    }
    final auth = await account.authentication;
    final credential = GoogleAuthProvider.credential(
      accessToken: auth.accessToken,
      idToken: auth.idToken,
    );
    final result = await FirebaseAuth.instance.signInWithCredential(credential);
    final email = result.user?.email;
    if (!isAllowedSchoolEmail(email)) {
      await FirebaseAuth.instance.signOut();
      await google.signOut();
      throw StateError(
        'Chỉ chấp nhận tài khoản Google $allowedEmailSuffix (email hiện tại: $email).',
      );
    }
    return result;
  }

  static Future<void> signOut() async {
    try {
      await _googleClient?.signOut();
    } catch (_) {}
    await FirebaseAuth.instance.signOut();
  }
}
