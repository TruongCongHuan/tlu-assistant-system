// lib/screens/notifications_screen.dart
import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../data/demo_school_notifications.dart';
import '../models/school_notification_item.dart';
import '../services/local_notification_badge_service.dart';
import '../services/local_notifications_repository.dart';
import '../services/student_alert_service.dart';
import '../theme/app_theme.dart';

const _kNotificationsCollection = 'school_notifications';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  Timer? _pollTimer;
  List<SchoolNotificationItem> _items = [];
  final Set<String> _seenIds = {};
  Object? _error;
  var _loading = true;

  @override
  void initState() {
    super.initState();
    if (AppRuntimeConfig.useLocalApi) {
      _loadLocal().then((_) async {
        final items = await LocalNotificationsRepository.fetchAll();
        await LocalNotificationBadgeService.markAllSeen(
          items.map((e) => e.id).toList(),
        );
        await StudentAlertService.instance.refresh();
      });
      _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _loadLocal());
    }
  }

  Future<void> _loadLocal() async {
    try {
      final items = await LocalNotificationsRepository.fetchAll();
      if (!mounted) return;
      for (final n in items) {
        if (!_seenIds.contains(n.id) && _seenIds.isNotEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Thông báo mới: ${n.title}'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        _seenIds.add(n.id);
      }
      setState(() {
        _items = items;
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e;
          _loading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (DemoReportConfig.enabled && AppRuntimeConfig.useStaticDemo) {
      return Scaffold(
        appBar: AppBar(
          leading: const BackButton(color: AppTheme.textPrimary),
          title: const Text('Thông báo'),
        ),
        body: _NotificationList(items: DemoSchoolNotifications.all()),
      );
    }

    if (AppRuntimeConfig.useLocalApi) {
      return Scaffold(
        appBar: AppBar(
          leading: const BackButton(color: AppTheme.textPrimary),
          title: const Text('Thông báo'),
        ),
        body: _loading
            ? const Center(
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppTheme.accent,
                ),
              )
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'Không tải được: $_error',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppTheme.accentRed),
                      ),
                    ),
                  )
                : _NotificationList(items: _items),
      );
    }

    if (Firebase.apps.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          leading: const BackButton(color: AppTheme.textPrimary),
          title: const Text('Thông báo'),
        ),
        body: const _FirebaseMissingBody(),
      );
    }

    final stream = FirebaseFirestore.instance
        .collection(_kNotificationsCollection)
        .orderBy('createdAt', descending: true)
        .snapshots();

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: const Text('Thông báo'),
      ),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: stream,
        builder: (context, snap) {
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Không tải được danh sách.\n${snap.error}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppTheme.textSecondary),
                ),
              ),
            );
          }
          if (!snap.hasData) {
            return const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.accent,
              ),
            );
          }
          final docs = snap.data!.docs;
          if (docs.isEmpty) {
            return const Center(
              child: Text(
                'Chưa có thông báo từ nhà trường.',
                style: TextStyle(color: AppTheme.textSecondary),
              ),
            );
          }

          final items = docs.map(SchoolNotificationItem.fromDoc).toList();
          return _NotificationList(items: items);
        },
      ),
    );
  }
}

class _NotificationList extends StatelessWidget {
  final List<SchoolNotificationItem> items;

  const _NotificationList({required this.items});

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const Center(
        child: Text(
          'Chưa có thông báo từ nhà trường.',
          style: TextStyle(color: AppTheme.textSecondary),
        ),
      );
    }

    final df = DateFormat('dd/MM/yyyy HH:mm');

    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(color: AppTheme.surfaceBorder),
      itemBuilder: (_, i) {
        final n = items[i];
        final subtitle = n.createdAt != null ? df.format(n.createdAt!) : '';
        return ListTile(
          title: Text(
            n.title,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (subtitle.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    subtitle,
                    style: const TextStyle(
                      color: AppTheme.textTertiary,
                      fontSize: 12,
                    ),
                  ),
                ),
              if (n.body.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    n.body,
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 14,
                    ),
                  ),
                ),
            ],
          ),
          trailing: n.link != null && n.link!.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.open_in_new_rounded,
                      color: AppTheme.accent, size: 22),
                  onPressed: () async {
                    final u = Uri.tryParse(n.link!);
                    if (u == null) return;
                    try {
                      await launchUrl(
                        u,
                        mode: LaunchMode.externalApplication,
                      );
                    } catch (_) {
                      if (context.mounted && AppRuntimeConfig.useFirebase) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Không mở được liên kết.'),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    }
                  },
                )
              : null,
        );
      },
    );
  }
}

class _FirebaseMissingBody extends StatelessWidget {
  const _FirebaseMissingBody();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(24),
      child: Center(
        child: Text(
          'Firebase chưa được cấu hình trên app.\n\n'
          'Thêm dart-define FIREBASE_API_KEY, FIREBASE_APP_ID, '
          'FIREBASE_MESSAGING_SENDER_ID, FIREBASE_PROJECT_ID khi chạy, '
          'hoặc dùng FlutterFire CLI.\n\n'
          'Collection Firestore: "$_kNotificationsCollection" '
          '(trường: title, body, createdAt, link?).',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
        ),
      ),
    );
  }
}
