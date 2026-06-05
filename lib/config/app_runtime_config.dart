// lib/config/app_runtime_config.dart
/// Chế độ backend — đổi [backend] khi chuyển demo / production.
enum AppBackend {
  /// Dữ liệu tĩnh trong app (chụp báo cáo).
  staticDemo,

  /// Docker BFF + JSON trên ổ đĩa (quay demo tối nay).
  localApi,

  /// Firebase production.
  firebase,
}

class AppRuntimeConfig {
  AppRuntimeConfig._();

  /// Tối nay: localApi. Mai: firebase. Chụp ảnh: staticDemo.
  static const AppBackend backend = AppBackend.localApi;

  static const String studentUid = 'demo_student_257480001';

  static const String bffBaseUrl = String.fromEnvironment(
    'BFF_BASE_URL',
    defaultValue: 'http://192.168.1.42:3000',
  );

  static const String studentApiKey = String.fromEnvironment(
    'STUDENT_API_KEY',
    defaultValue: 'dev-student-key',
  );

  static bool get useLocalApi => backend == AppBackend.localApi;

  static bool get useStaticDemo => backend == AppBackend.staticDemo;

  static bool get useFirebase => backend == AppBackend.firebase;

  static bool get isBffConfigured =>
      bffBaseUrl.isNotEmpty && studentApiKey.isNotEmpty;
}
