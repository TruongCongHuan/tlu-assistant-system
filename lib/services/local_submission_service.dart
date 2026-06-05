// lib/services/local_submission_service.dart
import 'package:http/http.dart' as http;

import 'student_api_client.dart';

class LocalSubmissionService {
  LocalSubmissionService._();

  static Future<String> submit({
    required String title,
    required String details,
    required List<http.MultipartFile> files,
  }) async {
    final j = await StudentApiClient.postMultipart(
      '/api/student/submissions',
      fields: {'title': title, 'details': details},
      files: files,
    );
    return j['id'] as String? ?? '';
  }
}
