// lib/services/user_profile_sync.dart
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';

/// Đồng bộ [users/{uid}] sau đăng nhập Google (kế hoạch RBAC / Dashboard cán bộ).
class UserProfileSync {
  UserProfileSync._();

  static Future<void> ensureForCurrentUser(User user) async {
    if (Firebase.apps.isEmpty) return;
    final ref = FirebaseFirestore.instance.collection('users').doc(user.uid);
    final snap = await ref.get();
    await ref.set(
      {
        'email': user.email,
        'displayName': user.displayName ?? (user.isAnonymous ? 'Sinh viên' : null),
        'photoUrl': user.photoURL,
        'role': 'student',
        'updatedAt': FieldValue.serverTimestamp(),
        'source': user.isAnonymous ? 'anonymous' : 'google',
        if (!snap.exists) 'createdAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
  }
}
