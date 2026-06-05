// lib/config/demo_report_config.dart
/// Bật để chụp màn hình báo cáo — không cần Firebase / backend.
/// Đặt [enabled] = false khi demo xong.
class DemoReportConfig {
  DemoReportConfig._();

  /// Chỉ bật khi chụp báo cáo tĩnh. Demo tối nay dùng [AppRuntimeConfig.localApi].
  static const bool enabled = false;

  static const studentName = 'Nguyễn Minh Anh';
  static const studentShortName = 'Minh Anh';
  static const studentId = '257480001';
  static const studentProgram = 'Khoa học Máy tính';
  static const studentYear = 'năm nhất';
  static const studentEmail = 'minhanh.nguyen@thanglong.edu.vn';
}
