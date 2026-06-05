// lib/widgets/notification_bell_button.dart
import 'package:flutter/material.dart';

import '../config/app_runtime_config.dart';
import '../services/student_alert_service.dart';
import '../theme/app_theme.dart';
import '../screens/notifications_screen.dart';

class NotificationBellButton extends StatelessWidget {
  const NotificationBellButton({super.key});

  @override
  Widget build(BuildContext context) {
    if (!AppRuntimeConfig.useLocalApi) {
      return IconButton(
        icon: const Icon(
          Icons.notifications_outlined,
          color: AppTheme.textSecondary,
        ),
        tooltip: 'Thông báo',
        onPressed: () {
          Navigator.push<void>(
            context,
            MaterialPageRoute<void>(
              builder: (_) => const NotificationsScreen(),
            ),
          );
        },
      );
    }

    return ListenableBuilder(
      listenable: StudentAlertService.instance,
      builder: (context, _) {
        final unread = StudentAlertService.instance.totalUnread;
        return Stack(
          clipBehavior: Clip.none,
          children: [
            IconButton(
              icon: const Icon(
                Icons.notifications_outlined,
                color: AppTheme.textSecondary,
              ),
              tooltip: unread > 0 ? 'Thông báo ($unread)' : 'Thông báo',
              onPressed: () async {
                await Navigator.push<void>(
                  context,
                  MaterialPageRoute<void>(
                    builder: (_) => const NotificationsScreen(),
                  ),
                );
                await StudentAlertService.instance.refresh();
              },
            ),
            if (unread > 0)
              Positioned(
                right: 6,
                top: 6,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.accentRed,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                  child: Text(
                    unread > 99 ? '99+' : '$unread',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
