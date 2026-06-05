// lib/config/department_catalog.dart
/// ID phòng ban ổn định — khớp seed `departments` trên Firestore / BFF staff-console.
class DepartmentEntry {
  final String id;
  final String title;

  const DepartmentEntry({required this.id, required this.title});
}

class DepartmentCatalog {
  DepartmentCatalog._();

  static const List<DepartmentEntry> all = [
    DepartmentEntry(id: 'co_van', title: 'Cố vấn học tập'),
    DepartmentEntry(
      id: 'ct_sv',
      title: 'Phòng Công tác Chính trị Sinh viên',
    ),
    DepartmentEntry(id: 'dao_tao', title: 'Phòng Đào tạo'),
    DepartmentEntry(
      id: 'tai_chinh',
      title: 'Phòng Tài chính - Kế toán',
    ),
    DepartmentEntry(id: 'tam_ly', title: 'Phòng Tham vấn tâm lý'),
  ];

  /// Trả về [id] khớp [departmentTitle] từ drawer; null nếu không khớp.
  static String? idForTitle(String departmentTitle) {
    final t = departmentTitle.trim();
    for (final e in all) {
      if (e.title == t) return e.id;
    }
    return null;
  }

  static String? titleForId(String id) {
    for (final e in all) {
      if (e.id == id) return e.title;
    }
    return null;
  }
}
