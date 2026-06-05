// lib/config/firebase_bootstrap.dart
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

import '../firebase_options.dart';

/// Khởi tạo Firebase.
///
/// **Ưu tiên:** [DefaultFirebaseOptions] (từ google-services.json) — tránh lỗi Android
/// khi Gradle không merge `google_app_id` vào APK.
///
/// **Fallback:** native (plist) hoặc `--dart-define` FIREBASE_*.
class FirebaseBootstrap {
  FirebaseBootstrap._();

  static bool ready = false;

  static Future<void> ensureInitialized() async {
    try {
      if (Firebase.apps.isNotEmpty) {
        return;
      }

      try {
        await Firebase.initializeApp(
          options: DefaultFirebaseOptions.currentPlatform,
        );
        if (kDebugMode) {
          debugPrint(
            '[Firebase] Đã khởi tạo từ firebase_options '
            '(project=${DefaultFirebaseOptions.android.projectId}).',
          );
        }
        return;
      } catch (e) {
        if (kDebugMode) {
          debugPrint('[Firebase] firebase_options thất bại ($e) — thử native…');
        }
      }

      try {
        await Firebase.initializeApp();
        if (kDebugMode) {
          debugPrint('[Firebase] Đã khởi tạo từ cấu hình native (google-services / plist).');
        }
        return;
      } catch (e) {
        if (kDebugMode) {
          debugPrint('[Firebase] Không init từ native ($e) — thử dart-define…');
        }
      }

      const apiKey = String.fromEnvironment('FIREBASE_API_KEY', defaultValue: '');
      const appId = String.fromEnvironment('FIREBASE_APP_ID', defaultValue: '');
      const senderId =
          String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID', defaultValue: '');
      const projectId =
          String.fromEnvironment('FIREBASE_PROJECT_ID', defaultValue: '');

      if (apiKey.isEmpty || appId.isEmpty || senderId.isEmpty || projectId.isEmpty) {
        if (kDebugMode) {
          debugPrint(
            '[Firebase] Chưa init được: thêm google-services.json + plugin Gradle (Android), '
            'hoặc đặt FIREBASE_API_KEY / FIREBASE_APP_ID / FIREBASE_MESSAGING_SENDER_ID / '
            'FIREBASE_PROJECT_ID (dart-define).',
          );
        }
        return;
      }

      const storageBucket =
          String.fromEnvironment('FIREBASE_STORAGE_BUCKET', defaultValue: '');
      final bucket =
          storageBucket.isNotEmpty ? storageBucket : '$projectId.appspot.com';

      await Firebase.initializeApp(
        options: FirebaseOptions(
          apiKey: apiKey,
          appId: appId,
          messagingSenderId: senderId,
          projectId: projectId,
          storageBucket: bucket,
        ),
      );
      if (kDebugMode) {
        debugPrint('[Firebase] Đã khởi tạo từ dart-define, project=$projectId');
      }
    } finally {
      ready = Firebase.apps.isNotEmpty;
    }
  }
}
