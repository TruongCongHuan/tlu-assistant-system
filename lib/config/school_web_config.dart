// lib/config/school_web_config.dart
/// URL các trang nhúng WebView — ghi đè khi build:
/// `flutter run --dart-define=SCHOOL_URL_ELEARNING=https://...`
class SchoolWebConfig {
  SchoolWebConfig._();

  /// E-Learning / học trực tuyến
  static const String elearning = String.fromEnvironment(
    'SCHOOL_URL_ELEARNING',
    defaultValue: 'https://elearning.thanglong.edu.vn/login/index.php',
  );

  /// Đăng ký học phần / môn học
  static const String courseRegistration = String.fromEnvironment(
    'SCHOOL_URL_REGISTRATION',
    defaultValue: 'https://dangkyhoc.thanglong.edu.vn/',
  );

  /// Thanh toán học phí
  static const String tuitionPayment = String.fromEnvironment(
    'SCHOOL_URL_TUITION',
    defaultValue: 'https://e-bills.vn/pay/thanglong',
  );
}
