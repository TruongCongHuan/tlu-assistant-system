// lib/main.dart
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'theme/app_theme.dart';
import 'config/app_runtime_config.dart';
import 'config/demo_report_config.dart';
import 'config/firebase_bootstrap.dart';
import 'widgets/firebase_auth_gate.dart';
import 'providers/chat_provider.dart';
import 'services/firebase_session_service.dart';
import 'services/push_notification_service.dart';
import 'services/student_alert_service.dart';
import 'services/tts_service.dart';
import 'services/stt_service.dart';
import 'services/user_profile_sync.dart';
import 'screens/home_screen.dart';
import 'screens/pdf_manager_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (AppRuntimeConfig.useFirebase) {
    await FirebaseBootstrap.ensureInitialized();
  }

  if (AppRuntimeConfig.useFirebase && Firebase.apps.isNotEmpty) {
    try {
      final u = await FirebaseSessionService.ensureSignedIn();
      if (u != null) {
        await UserProfileSync.ensureForCurrentUser(u);
        await PushNotificationService.init();
      }
    } catch (e, st) {
      if (kDebugMode) debugPrint('[main] auth/push bootstrap: $e $st');
    }
  }

  final prefs = await SharedPreferences.getInstance();
  if (AppRuntimeConfig.useLocalApi) {
    await prefs.setBool('use_remote_rag', true);
    await StudentAlertService.instance.init();
  }
  // Mặc định RAG qua server; LocalRagService chỉ còn legacy (không hiển thị trong UI).
  final useRemoteRag = prefs.getBool('use_remote_rag') ?? true;
  if (!prefs.containsKey('use_remote_rag')) {
    await prefs.setBool('use_remote_rag', true);
  }

  // Full screen immersive — giống Gemini
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: AppTheme.background,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  // Lock portrait (landscape optional sau này)
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => TtsService()),
        ChangeNotifierProvider(create: (_) => SttService()),
        ChangeNotifierProvider(
          create: (_) => ChatProvider(
            initialUseRemoteRag: DemoReportConfig.enabled
                ? false
                : (AppRuntimeConfig.useLocalApi ? true : useRemoteRag),
          ),
        ),
      ],
      child: const TluAiApp(),
    ),
  );
}

class TluAiApp extends StatelessWidget {
  const TluAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TLU AI Assistant',
      theme: AppTheme.dark,
      debugShowCheckedModeBanner: false,
      builder: (context, child) => FirebaseAuthGate.wrap(child),
      routes: {
        '/':    (_) => const HomeScreen(),
        '/pdf': (_) => const PdfManagerScreen(),
      },
      initialRoute: '/',
    );
  }
}
