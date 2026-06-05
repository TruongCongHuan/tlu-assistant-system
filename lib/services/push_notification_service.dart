// lib/services/push_notification_service.dart
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

/// FCM: lưu token lên [users/{uid}], đăng ký topic thông báo trường (admin gửi qua staff-console).
class PushNotificationService {
  PushNotificationService._();

  static const String schoolTopic = 'school_broadcast';

  static Future<void> init() async {
    if (FirebaseAuth.instance.currentUser == null) return;

    final msg = FirebaseMessaging.instance;
    await msg.setAutoInitEnabled(true);

    if (!kIsWeb) {
      final settings = await msg.requestPermission(alert: true, badge: true, sound: true);
      if (kDebugMode) {
        debugPrint('[FCM] permission: ${settings.authorizationStatus}');
      }
    }

    await _persistToken(await msg.getToken());
    FirebaseMessaging.instance.onTokenRefresh.listen(_persistToken);

    try {
      await msg.subscribeToTopic(schoolTopic);
      if (kDebugMode) debugPrint('[FCM] subscribed topic=$schoolTopic');
    } catch (e) {
      if (kDebugMode) debugPrint('[FCM] subscribe topic failed: $e');
    }

    FirebaseMessaging.onMessage.listen((RemoteMessage m) {
      if (kDebugMode) {
        debugPrint('[FCM] foreground: ${m.notification?.title} ${m.notification?.body}');
      }
    });
  }

  static Future<void> _persistToken(String? token) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null || token == null || token.isEmpty) return;
    try {
      await FirebaseFirestore.instance.collection('users').doc(uid).set(
        {
          'fcmToken': token,
          'fcmTokenUpdatedAt': FieldValue.serverTimestamp(),
        },
        SetOptions(merge: true),
      );
    } catch (e) {
      if (kDebugMode) debugPrint('[FCM] persist token failed: $e');
    }
  }
}
