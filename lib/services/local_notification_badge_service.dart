// lib/services/local_notification_badge_service.dart
import 'package:shared_preferences/shared_preferences.dart';

import 'local_notifications_repository.dart';

const _kSeenNotificationIds = 'seen_notification_ids';

class LocalNotificationBadgeService {
  LocalNotificationBadgeService._();

  static const String seenStorageKey = _kSeenNotificationIds;

  static Future<int> unreadCount() async {
    final prefs = await SharedPreferences.getInstance();
    final seen = prefs.getStringList(_kSeenNotificationIds) ?? [];
    final items = await LocalNotificationsRepository.fetchAll();
    return items.where((n) => !seen.contains(n.id)).length;
  }

  static Future<void> markAllSeen(List<String> ids) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_kSeenNotificationIds, ids);
  }

  static Future<void> markSeen(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final seen = <String>{
      ...(prefs.getStringList(_kSeenNotificationIds) ?? <String>[]),
      id,
    };
    await prefs.setStringList(_kSeenNotificationIds, seen.toList());
  }
}
