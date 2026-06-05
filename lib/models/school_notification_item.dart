// lib/models/school_notification_item.dart
import 'package:cloud_firestore/cloud_firestore.dart';

class SchoolNotificationItem {
  final String id;
  final String title;
  final String body;
  final DateTime? createdAt;
  final String? link;

  const SchoolNotificationItem({
    required this.id,
    required this.title,
    required this.body,
    this.createdAt,
    this.link,
  });

  factory SchoolNotificationItem.fromDoc(
    QueryDocumentSnapshot<Map<String, dynamic>> doc,
  ) {
    final d = doc.data();
    final ts = d['createdAt'];
    DateTime? at;
    if (ts is Timestamp) at = ts.toDate();

    return SchoolNotificationItem(
      id: doc.id,
      title: (d['title'] as String?)?.trim().isNotEmpty == true
          ? d['title'] as String
          : 'Thông báo',
      body: (d['body'] as String?) ?? '',
      createdAt: at,
      link: d['link'] as String?,
    );
  }
}
