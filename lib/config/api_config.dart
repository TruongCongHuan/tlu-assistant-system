/// Build-time config for remote RAG API (Cloud Run / local Docker).
///
/// ```bash
/// flutter run --dart-define=API_BASE_URL=https://xxx.run.app \
///   --dart-define=STUDENT_API_KEY=your-student-secret
/// ```
class ApiConfig {
  ApiConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static const String studentApiKey = String.fromEnvironment(
    'STUDENT_API_KEY',
    defaultValue: '',
  );

  static bool get isRemoteConfigured =>
      apiBaseUrl.isNotEmpty && studentApiKey.isNotEmpty;

  static Uri get chatStreamUri =>
      Uri.parse('${apiBaseUrl.replaceAll(RegExp(r'/$'), '')}/v1/chat/stream');
}
