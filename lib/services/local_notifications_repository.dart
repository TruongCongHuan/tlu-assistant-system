// lib/services/local_notifications_repository.dart
import '../models/school_notification_item.dart';
import 'student_api_client.dart';

class LocalNotificationsRepository {
  LocalNotificationsRepository._();

  static Future<List<SchoolNotificationItem>> fetchAll() async {
    final j = await StudentApiClient.getJson('/api/student/notifications');
    final items = j['items'] as List<dynamic>? ?? [];
    return items.map((e) {
      final m = e as Map<String, dynamic>;
      return SchoolNotificationItem(
        id: m['id'] as String? ?? '',
        title: m['title'] as String? ?? '',
        body: m['body'] as String? ?? '',
        link: m['link'] as String?,
        createdAt: DateTime.tryParse(m['createdAt'] as String? ?? ''),
      );
    }).toList();
  }
}
