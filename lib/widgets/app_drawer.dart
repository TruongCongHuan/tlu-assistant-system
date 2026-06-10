// lib/widgets/app_drawer.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import '../config/app_runtime_config.dart';
import '../config/department_catalog.dart';
import '../config/demo_report_config.dart';
import '../theme/app_theme.dart';
import '../services/student_alert_service.dart';
import '../services/school_auth_service.dart';
import '../config/school_web_config.dart';
import '../screens/pdf_manager_screen.dart';
import '../screens/chat_screen.dart';
import '../screens/department_chat_screen.dart';
import '../screens/school_webview_screen.dart';
import '../screens/application_form_screen.dart';
import '../screens/feedback_letter_screen.dart';

void _openWeb(BuildContext context, String title, String url) {
  Navigator.pop(context);
  Navigator.push(
    context,
    MaterialPageRoute<void>(
      builder: (_) => SchoolWebViewScreen(title: title, initialUrl: url),
    ),
  );
}

void _openDepartmentChat(BuildContext context, String departmentTitle) {
  Navigator.pop(context);
  Navigator.push(
    context,
    MaterialPageRoute<void>(
      builder: (_) => DepartmentChatScreen(departmentTitle: departmentTitle),
    ),
  );
}

class AppDrawer extends StatefulWidget {
  const AppDrawer({super.key});

  @override
  State<AppDrawer> createState() => _AppDrawerState();
}

class _AppDrawerState extends State<AppDrawer> {
  int _unreadForTitle(String title) {
    if (!AppRuntimeConfig.useLocalApi) return 0;
    final id = DepartmentCatalog.idForTitle(title);
    if (id == null) return 0;
    return StudentAlertService.instance.unreadByDeptId[id] ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    if (AppRuntimeConfig.useLocalApi) {
      return ListenableBuilder(
        listenable: StudentAlertService.instance,
        builder: (context, _) => _drawer(context),
      );
    }
    return _drawer(context);
  }

  Widget _drawer(BuildContext context) {
    return Drawer(
      width: MediaQuery.of(context).size.width * 0.82,
      child: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 12),

              if (DemoReportConfig.enabled || AppRuntimeConfig.useLocalApi)
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF1E5FC4), Color(0xFF7B1FA2)],
                          ),
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: const Center(
                          child: Text(
                            'MA',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              DemoReportConfig.studentName,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontWeight: FontWeight.w600,
                                fontSize: 15,
                              ),
                            ),
                            Text(
                              '${DemoReportConfig.studentProgram} · ${DemoReportConfig.studentYear}',
                              style: const TextStyle(
                                color: AppTheme.textTertiary,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              'MSSV ${DemoReportConfig.studentId}',
                              style: const TextStyle(
                                color: AppTheme.textTertiary,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                  collapsedIconColor: AppTheme.textPrimary,
                  iconColor: AppTheme.textPrimary,
                  leading: const Icon(Icons.forum_outlined,
                      color: AppTheme.textPrimary, size: 22),
                  title: const Text(
                    'Chat',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  subtitle: const Text(
                    'TLU AI & các phòng ban',
                    style: TextStyle(color: AppTheme.textTertiary, fontSize: 11),
                  ),
                  children: [
                    _DrawerChildTile(
                      label: 'TLU AI Assistant',
                      onTap: () {
                        Navigator.pop(context);
                        Navigator.push(
                          context,
                          MaterialPageRoute<void>(
                            builder: (_) => const ChatScreen(),
                          ),
                        );
                      },
                    ),
                    _DrawerChildTile(
                      label: 'Cố vấn học tập',
                      unread: _unreadForTitle('Cố vấn học tập'),
                      onTap: () => _openDepartmentChat(context, 'Cố vấn học tập'),
                    ),
                    _DrawerChildTile(
                      label: 'Phòng Công tác Chính trị Sinh viên',
                      unread: _unreadForTitle('Phòng Công tác Chính trị Sinh viên'),
                      onTap: () => _openDepartmentChat(
                        context,
                        'Phòng Công tác Chính trị Sinh viên',
                      ),
                    ),
                    _DrawerChildTile(
                      label: 'Phòng Đào tạo',
                      unread: _unreadForTitle('Phòng Đào tạo'),
                      onTap: () =>
                          _openDepartmentChat(context, 'Phòng Đào tạo'),
                    ),
                    _DrawerChildTile(
                      label: 'Phòng Tài chính - Kế toán',
                      unread: _unreadForTitle('Phòng Tài chính - Kế toán'),
                      onTap: () => _openDepartmentChat(
                        context,
                        'Phòng Tài chính - Kế toán',
                      ),
                    ),
                    _DrawerChildTile(
                      label: 'Phòng Tham vấn tâm lý',
                      unread: _unreadForTitle('Phòng Tham vấn tâm lý'),
                      onTap: () => _openDepartmentChat(
                        context,
                        'Phòng Tham vấn tâm lý',
                      ),
                    ),
                  ],
                ),
              ),

              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                  collapsedIconColor: AppTheme.textPrimary,
                  iconColor: AppTheme.textPrimary,
                  leading: const Icon(Icons.public_rounded,
                      color: AppTheme.textPrimary, size: 22),
                  title: const Text(
                    'Cổng thông tin trực tuyến',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  children: [
                    _DrawerChildTile(
                      label: 'E-Learning',
                      onTap: () => _openWeb(
                        context,
                        'E-Learning',
                        SchoolWebConfig.elearning,
                      ),
                    ),
                    _DrawerChildTile(
                      label: 'Đăng ký học',
                      onTap: () => _openWeb(
                        context,
                        'Đăng ký học',
                        SchoolWebConfig.courseRegistration,
                      ),
                    ),
                    _DrawerChildTile(
                      label: 'Thanh toán học phí',
                      onTap: () => _openWeb(
                        context,
                        'Thanh toán học phí',
                        SchoolWebConfig.tuitionPayment,
                      ),
                    ),
                  ],
                ),
              ),

              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                  collapsedIconColor: AppTheme.textPrimary,
                  iconColor: AppTheme.textPrimary,
                  leading: const Icon(Icons.mail_outline_rounded,
                      color: AppTheme.textPrimary, size: 22),
                  title: const Text(
                    'Đơn từ & ý kiến',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  children: [
                    _DrawerChildTile(
                      label: 'Gửi đơn từ',
                      onTap: () {
                        Navigator.pop(context);
                        Navigator.push(
                          context,
                          MaterialPageRoute<void>(
                            builder: (_) => const ApplicationFormScreen(),
                          ),
                        );
                      },
                    ),
                    _DrawerChildTile(
                      label: 'Gửi thư góp ý',
                      onTap: () {
                        Navigator.pop(context);
                        Navigator.push(
                          context,
                          MaterialPageRoute<void>(
                            builder: (_) => const FeedbackLetterScreen(),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),

              _DrawerTile(
                icon: Icons.description_outlined,
                label: 'Quản lý Tài liệu',
                trailing: const Icon(Icons.chevron_right,
                    color: AppTheme.textTertiary, size: 20),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute<void>(
                      builder: (_) => const PdfManagerScreen(),
                    ),
                  );
                },
              ),

              if (!DemoReportConfig.enabled && Firebase.apps.isNotEmpty)
                Builder(
                  builder: (context) {
                    final u = FirebaseAuth.instance.currentUser;
                    if (u == null) return const SizedBox.shrink();
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 16),
                          child: Divider(color: AppTheme.surfaceBorder),
                        ),
                        ListTile(
                          leading: const Icon(Icons.person_outline,
                              color: AppTheme.textSecondary),
                          title: Text(
                            u.isAnonymous
                                ? 'Phiên ẩn danh (${u.uid.substring(0, 8)}…)'
                                : (u.email ?? ''),
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: const Text(
                            'Đăng xuất (sẽ tạo phiên mới)',
                            style: TextStyle(
                              color: AppTheme.textTertiary,
                              fontSize: 12,
                            ),
                          ),
                          onTap: () async {
                            Navigator.pop(context);
                            await SchoolAuthService.signOut();
                          },
                        ),
                      ],
                    );
                  },
                ),

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _DrawerChildTile extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final int unread;

  const _DrawerChildTile({
    required this.label,
    required this.onTap,
    this.unread = 0,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      contentPadding: const EdgeInsets.only(left: 56, right: 16),
      title: Text(
        label,
        style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (unread > 0)
            Container(
              margin: const EdgeInsets.only(right: 6),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.accentRed,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                unread > 99 ? '99+' : '$unread',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          const Icon(Icons.chevron_right,
              color: AppTheme.textTertiary, size: 18),
        ],
      ),
      onTap: onTap,
    );
  }
}

class _DrawerTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final Widget? trailing;
  final VoidCallback onTap;

  const _DrawerTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.textPrimary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label,
                  style: const TextStyle(
                      color: AppTheme.textPrimary, fontSize: 15)),
            ),
            if (trailing != null) trailing!,
          ],
        ),
      ),
    );
  }
}
