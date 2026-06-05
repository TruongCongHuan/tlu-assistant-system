// lib/services/local_feedback_service.dart
import 'student_api_client.dart';

class LocalFeedbackService {
  LocalFeedbackService._();

  static Future<String> submit({
    required String subject,
    required String body,
    required bool anonymous,
    String? studentLabel,
  }) async {
    final j = await StudentApiClient.postJson('/api/student/feedback', {
      'subject': subject,
      'body': body,
      'anonymous': anonymous,
      if (studentLabel != null) 'studentLabel': studentLabel,
    });
    return j['id'] as String? ?? '';
  }
}
