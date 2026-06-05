// lib/services/department_chat_repository.dart
// PRODUCTION_FIREBASE — dùng khi AppRuntimeConfig.useFirebase
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';

import 'firebase_session_service.dart';

/// Chat SV → phòng ban: [department_threads] + subcollection [messages].
class DepartmentChatRepository {
  DepartmentChatRepository._();

  static CollectionReference<Map<String, dynamic>> get _threads =>
      FirebaseFirestore.instance.collection('department_threads');

  static Future<String> ensureThread({
    required String departmentId,
    required String departmentTitle,
  }) async {
    if (Firebase.apps.isEmpty) {
      throw StateError('Chưa cấu hình Firebase.');
    }
    final user = await FirebaseSessionService.ensureSignedIn();
    if (user == null) {
      throw StateError(
        'Chưa đăng nhập. Bật Anonymous trong Firebase Console → Authentication.',
      );
    }

    // ID cố định: tránh query collection (dễ bị rules từ chối) + khớp staff-console .doc(id).
    final threadId = '${user.uid}_$departmentId';
    final ref = _threads.doc(threadId);
    final snap = await ref.get();
    if (!snap.exists) {
      await ref.set({
        'studentUid': user.uid,
        'studentEmail': user.email ?? '',
        'departmentId': departmentId,
        'departmentTitle': departmentTitle,
        'status': 'open',
        'preview': '',
        'createdAt': FieldValue.serverTimestamp(),
        'lastMessageAt': FieldValue.serverTimestamp(),
      });
    }
    return threadId;
  }

  static Stream<QuerySnapshot<Map<String, dynamic>>> messagesStream(
    String threadId,
  ) {
    return _threads
        .doc(threadId)
        .collection('messages')
        .orderBy('createdAt')
        .snapshots();
  }

  static Future<void> sendStudentMessage({
    required String threadId,
    required String text,
  }) async {
    final user = await FirebaseSessionService.ensureSignedIn();
    if (user == null) {
      throw StateError(
        'Chưa đăng nhập. Bật Anonymous trong Firebase Console → Authentication.',
      );
    }
    final batch = FirebaseFirestore.instance.batch();
    final threadRef = _threads.doc(threadId);
    final msgRef = threadRef.collection('messages').doc();
    batch.set(msgRef, {
      'text': text,
      'senderUid': user.uid,
      'senderRole': 'student',
      'senderName': user.displayName ?? user.email ?? 'Sinh viên',
      'createdAt': FieldValue.serverTimestamp(),
    });
    batch.set(
      threadRef,
      {
        'preview': text.length > 200 ? '${text.substring(0, 200)}…' : text,
        'lastMessageAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
    await batch.commit();
  }
}
