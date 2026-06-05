// lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../theme/app_theme.dart';
import '../widgets/app_drawer.dart';
import '../widgets/notification_bell_button.dart';
import '../widgets/quick_action_chip.dart';
import '../widgets/bottom_input_bar.dart';
import 'chat_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _inputCtrl = TextEditingController();

  final List<Map<String, String>> _actions = [
    {'emoji': '📄', 'label': 'Hỏi từ tài liệu'},
    {'emoji': '✨', 'label': 'Tóm tắt nội dung môn học'},
    {'emoji': '🧮', 'label': 'Giải bài tập từng bước'},
    {'emoji': '📝', 'label': 'Tạo đề cương ôn thi'},
    {'emoji': '🎓', 'label': 'Giải thích khái niệm khó'},
  ];

  @override
  void dispose() {
    _inputCtrl.dispose();
    super.dispose();
  }

  void _navigateToChat(String initialText) {
    if (initialText.trim().isEmpty) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatScreen(initialMessage: initialText.trim()),
      ),
    );
    _inputCtrl.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Builder(
          builder: (ctx) => IconButton(
            icon: const Icon(Icons.menu_rounded, color: AppTheme.textPrimary),
            onPressed: () => Scaffold.of(ctx).openDrawer(),
          ),
        ),
        title: const Text('TLU AI Assistant'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: GestureDetector(
              onTap: () {},
              child: Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1E5FC4), Color(0xFF7B1FA2)],
                  ),
                  borderRadius: BorderRadius.circular(17),
                ),
                child: Center(
                  child: Text(
                    (DemoReportConfig.enabled || AppRuntimeConfig.useLocalApi)
                        ? 'MA'
                        : 'SV',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const NotificationBellButton(),
        ],
      ),
      drawer: const AppDrawer(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              (DemoReportConfig.enabled || AppRuntimeConfig.useLocalApi)
                  ? 'Xin chào, ${DemoReportConfig.studentShortName}!'
                  : 'Xin chào, Sinh viên!',
              style: TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 17,
              ),
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),
            const SizedBox(height: 8),
            Text(
              (DemoReportConfig.enabled || AppRuntimeConfig.useLocalApi)
                  ? 'SV ${DemoReportConfig.studentYear}\n${DemoReportConfig.studentProgram}'
                  : 'Chúng ta nên bắt đầu\ntừ đâu nhỉ?',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 30,
                fontWeight: FontWeight.bold,
                height: 1.3,
              ),
            ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.1, end: 0),
            const SizedBox(height: 32),
            ...List.generate(_actions.length, (i) {
              return QuickActionChip(
                emoji: _actions[i]['emoji']!,
                label: _actions[i]['label']!,
                onTap: () => _navigateToChat(_actions[i]['label']!),
              ).animate().fadeIn(
                    delay: Duration(milliseconds: 300 + i * 80),
                    duration: 350.ms,
                  );
            }),
          ],
        ),
      ),
      bottomNavigationBar: BottomInputBar(
        controller: _inputCtrl,
        onSend: () => _navigateToChat(_inputCtrl.text),
        onAttachPdf: () => Navigator.pushNamed(context, '/pdf'),
      ),
    );
  }
}
