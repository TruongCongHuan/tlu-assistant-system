// lib/services/firebase_session_service.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

/// Đảm bảo có phiên Firebase (ưu tiên Anonymous) trước Firestore / FCM.
class FirebaseSessionService {
  FirebaseSessionService._();

  static Future<User?> ensureSignedIn() async {
    if (Firebase.apps.isEmpty) return null;

    final existing = FirebaseAuth.instance.currentUser;
    if (existing != null) return existing;

    try {
      final cred = await FirebaseAuth.instance.signInAnonymously();
      if (kDebugMode) {
        debugPrint('[FirebaseSession] Anonymous uid=${cred.user?.uid}');
      }
      return cred.user;
    } on FirebaseAuthException catch (e) {
      if (kDebugMode) {
        debugPrint('[FirebaseSession] signInAnonymously failed: ${e.code} ${e.message}');
      }
      rethrow;
    }
  }
}
