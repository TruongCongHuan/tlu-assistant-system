// lib/services/student_alert_service.dart
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_runtime_config.dart';
import 'local_chat_unread_service.dart';
import 'local_notification_badge_service.dart';
import 'local_notifications_repository.dart';

const _kDeptUnreadSnapshot = 'alert_dept_unread_snapshot';
const _kNotifiedSchoolIds = 'alert_notified_school_ids';

/// Poll BFF + hiện badge chuông + thông báo thanh trạng thái (local, không FCM).
class StudentAlertService extends ChangeNotifier {
  StudentAlertService._();
  static final StudentAlertService instance = StudentAlertService._();

  final FlutterLocalNotificationsPlugin _fln =
      FlutterLocalNotificationsPlugin();

  Timer? _timer;
  var _primed = false;
  var _schoolUnread = 0;
  var _chatUnread = 0;
  Map<String, int> _unreadByDeptId = {};
  Map<String, int> _lastDeptUnread = {};

  int get schoolUnread => _schoolUnread;
  int get chatUnread => _chatUnread;
  int get totalUnread => _schoolUnread + _chatUnread;
  Map<String, int> get unreadByDeptId => Map.unmodifiable(_unreadByDeptId);

  Future<void> init() async {
    if (!AppRuntimeConfig.useLocalApi) return;
    await _initNotifications();
    await _loadSnapshots();
    await refresh();
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => refresh());
  }

  Future<void> _initNotifications() async {
    if (Platform.isAndroid) {
      await Permission.notification.request();
    }

    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    await _fln.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );

    if (Platform.isAndroid) {
      const channel = AndroidNotificationChannel(
        'tlu_student_alerts',
        'Thông báo sinh viên',
        description: 'Tin nhắn phòng ban và thông báo nhà trường',
        importance: Importance.high,
        playSound: true,
        enableVibration: true,
      );
      await _fln
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(channel);
    }
  }

  Future<void> _loadSnapshots() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kDeptUnreadSnapshot);
    if (raw != null && raw.isNotEmpty) {
      for (final part in raw.split(',')) {
        final kv = part.split(':');
        if (kv.length == 2) {
          final n = int.tryParse(kv[1]);
          if (n != null) _lastDeptUnread[kv[0]] = n;
        }
      }
    }
  }

  Future<void> _saveDeptSnapshot() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = _lastDeptUnread.entries.map((e) => '${e.key}:${e.value}').join(',');
    await prefs.setString(_kDeptUnreadSnapshot, raw);
  }

  Future<Set<String>> _notifiedSchoolIds() async {
    final prefs = await SharedPreferences.getInstance();
    return {...?prefs.getStringList(_kNotifiedSchoolIds)};
  }

  Future<void> _addNotifiedSchoolId(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final set = {...?prefs.getStringList(_kNotifiedSchoolIds), id};
    await prefs.setStringList(_kNotifiedSchoolIds, set.toList());
  }

  /// Gọi sau khi mở màn thông báo / đọc chat để cập nhật badge ngay.
  Future<void> refresh() async {
    if (!AppRuntimeConfig.useLocalApi) return;
    try {
      final school = await LocalNotificationBadgeService.unreadCount();
      final chatItems = await LocalChatUnreadService.fetchSummary();
      final chatTotal =
          chatItems.fold<int>(0, (s, e) => s + e.unread);
      final byDept = {for (final e in chatItems) e.departmentId: e.unread};

      if (_primed) {
        await _maybeAlertSchool(school);
        await _maybeAlertChat(chatItems);
      } else {
        _primed = true;
      }

      _schoolUnread = school;
      _chatUnread = chatTotal;
      _unreadByDeptId = byDept;
      _lastDeptUnread = Map.from(byDept);
      await _saveDeptSnapshot();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) debugPrint('[StudentAlertService] refresh: $e');
    }
  }

  Future<void> _maybeAlertSchool(int unread) async {
    if (unread <= _schoolUnread) return;
    final items = await LocalNotificationsRepository.fetchAll();
    final prefs = await SharedPreferences.getInstance();
    final seen =
        prefs.getStringList(LocalNotificationBadgeService.seenStorageKey) ?? [];
    final alreadyNotified = await _notifiedSchoolIds();

    for (final n in items) {
      if (seen.contains(n.id) || alreadyNotified.contains(n.id)) continue;
      await _showTray(
        id: n.id.hashCode & 0x7fffffff,
        title: n.title.isNotEmpty ? n.title : 'Thông báo nhà trường',
        body: n.body.isNotEmpty ? n.body : 'Bạn có thông báo mới',
      );
      await _addNotifiedSchoolId(n.id);
      await SystemSound.play(SystemSoundType.alert);
    }
  }

  Future<void> _maybeAlertChat(List<DeptUnread> items) async {
    for (final d in items) {
      final prev = _lastDeptUnread[d.departmentId] ?? 0;
      if (d.unread > prev) {
        final title = d.departmentTitle.isNotEmpty
            ? d.departmentTitle
            : 'Phòng ban';
        final body = d.unread == 1
            ? 'Bạn có tin nhắn mới'
            : 'Bạn có ${d.unread} tin nhắn chưa đọc';
        await _showTray(
          id: (d.departmentId.hashCode ^ 0x5f3759df) & 0x7fffffff,
          title: title,
          body: body,
        );
        await SystemSound.play(SystemSoundType.alert);
      }
    }
  }

  Future<void> _showTray({
    required int id,
    required String title,
    required String body,
  }) async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        'tlu_student_alerts',
        'Thông báo sinh viên',
        channelDescription: 'Tin nhắn phòng ban và thông báo nhà trường',
        importance: Importance.high,
        priority: Priority.high,
        playSound: true,
        enableVibration: true,
        icon: '@mipmap/ic_launcher',
      ),
      iOS: DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      ),
    );
    await _fln.show(id, title, body, details);
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
