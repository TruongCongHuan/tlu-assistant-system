// lib/services/local_department_chat_repository.dart
import '../config/app_runtime_config.dart';
import 'student_api_client.dart';

class LocalChatMessage {
  LocalChatMessage({
    required this.id,
    required this.text,
    required this.senderRole,
    required this.senderName,
    required this.createdAt,
  });

  final String id;
  final String text;
  final String senderRole;
  final String? senderName;
  final DateTime? createdAt;

  factory LocalChatMessage.fromJson(Map<String, dynamic> j) {
    DateTime? at;
    final raw = j['createdAt'];
    if (raw is String) at = DateTime.tryParse(raw);
    return LocalChatMessage(
      id: j['id'] as String? ?? '',
      text: j['text'] as String? ?? '',
      senderRole: j['senderRole'] as String? ?? 'student',
      senderName: j['senderName'] as String?,
      createdAt: at,
    );
  }
}

class LocalDepartmentChatRepository {
  LocalDepartmentChatRepository._();

  static Future<String> departmentIdForTitle(String title) async {
    // Khớp DepartmentCatalog — import tại screen.
    return title;
  }

  static Future<List<LocalChatMessage>> fetchMessages(String departmentId) async {
    final j = await StudentApiClient.getJson(
      '/api/student/chat/threads/$departmentId/messages',
    );
    final items = j['items'] as List<dynamic>? ?? [];
    return items
        .map((e) => LocalChatMessage.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  static Future<void> sendMessage({
    required String departmentId,
    required String text,
  }) async {
    await StudentApiClient.postJson(
      '/api/student/chat/threads/$departmentId/messages',
      {'text': text},
    );
  }

  static String get studentUid => AppRuntimeConfig.studentUid;
}
