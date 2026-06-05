// lib/firebase_options.dart
// Cấu hình từ android/app/google-services.json (project tlu-ai-assistant).
// Dùng khi plugin Gradle không merge values.xml vào APK (lỗi FirebaseOptions from resource).
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError(
        'DefaultFirebaseOptions chưa cấu hình cho web.',
      );
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        return macos;
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions chưa hỗ trợ $defaultTargetPlatform.',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyDETIacj9kqR98hgNEc9Nf7HsFwOR9L2ko',
    appId: '1:958402253509:android:1f3cfcf58e27e38a0716ac',
    messagingSenderId: '958402253509',
    projectId: 'tlu-ai-assistant',
    storageBucket: 'tlu-ai-assistant.firebasestorage.app',
  );

  // Thêm GoogleService-Info.plist (iOS) hoặc chạy: dart pub global activate flutterfire_cli && flutterfire configure
  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyDETIacj9kqR98hgNEc9Nf7HsFwOR9L2ko',
    appId: '1:958402253509:android:1f3cfcf58e27e38a0716ac',
    messagingSenderId: '958402253509',
    projectId: 'tlu-ai-assistant',
    storageBucket: 'tlu-ai-assistant.firebasestorage.app',
  );

  static const FirebaseOptions macos = ios;
}
