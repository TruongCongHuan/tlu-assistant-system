// lib/services/local_chat_unread_service.dart
import 'student_api_client.dart';

class DeptUnread {
  DeptUnread({
    required this.departmentId,
    required this.departmentTitle,
    required this.unread,
  });

  final String departmentId;
  final String departmentTitle;
  final int unread;
}

class LocalChatUnreadService {
  LocalChatUnreadService._();

  static Future<List<DeptUnread>> fetchSummary() async {
    final j = await StudentApiClient.getJson('/api/student/chat/unread-summary');
    final items = j['items'] as List<dynamic>? ?? [];
    return items.map((e) {
      final m = e as Map<String, dynamic>;
      return DeptUnread(
        departmentId: m['departmentId'] as String? ?? '',
        departmentTitle: m['departmentTitle'] as String? ?? '',
        unread: (m['unread'] as num?)?.toInt() ?? 0,
      );
    }).toList();
  }

  static Future<int> totalUnread() async {
    final j = await StudentApiClient.getJson('/api/student/chat/unread-summary');
    return (j['totalUnread'] as num?)?.toInt() ?? 0;
  }
}
