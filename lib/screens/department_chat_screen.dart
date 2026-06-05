// lib/screens/department_chat_screen.dart
import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../config/department_catalog.dart';
import '../data/demo_department_chats.dart';
import '../models/conversation.dart';
import '../services/department_chat_repository.dart';
import '../services/local_department_chat_repository.dart';
import '../services/student_alert_service.dart';
import '../services/tts_service.dart';
import '../theme/app_theme.dart';
import '../widgets/bottom_input_bar.dart';
import '../widgets/chat_message_tile.dart';
import '../widgets/notification_bell_button.dart';

String abbreviateDepartmentName(String title) {
  final words =
      title.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();
  if (words.isEmpty) return '?';
  final buf = StringBuffer();
  for (final w in words) {
    if (buf.length >= 2) break;
    buf.write(w.characters.first.toUpperCase());
  }
  if (buf.length >= 2) return buf.toString().characters.take(2).toString();
  if (words.isNotEmpty) {
    final rest = words.first.characters.skip(1).take(1);
    if (rest.isNotEmpty) buf.write(rest.first.toUpperCase());
  }
  if (buf.isEmpty) return '?';
  return buf.toString().characters.take(2).toString();
}

List<Color> departmentAvatarGradient(String title) {
  const palettes = <List<Color>>[
    [Color(0xFF1565C0), Color(0xFF42A5F5)],
    [Color(0xFF2E7D32), Color(0xFF66BB6A)],
    [Color(0xFF6A1B9A), Color(0xFFAB47BC)],
    [Color(0xFFC62828), Color(0xFFEF5350)],
    [Color(0xFF00695C), Color(0xFF26A69A)],
    [Color(0xFFEF6C00), Color(0xFFFFB74D)],
    [Color(0xFF37474F), Color(0xFF78909C)],
  ];
  final i = title.hashCode.abs() % palettes.length;
  return palettes[i];
}

/// Chat phòng ban — demo báo cáo hoặc Firestore thật.
class DepartmentChatScreen extends StatefulWidget {
  final String departmentTitle;

  const DepartmentChatScreen({super.key, required this.departmentTitle});

  @override
  State<DepartmentChatScreen> createState() => _DepartmentChatScreenState();
}

class _DepartmentChatScreenState extends State<DepartmentChatScreen> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  var _sending = false;
  String? _threadId;
  Object? _initError;

  late final String _abbrev;
  late final List<Color> _gradient;
  String? _departmentId;
  TtsService? _tts;

  /// Chế độ demo tĩnh: tin nhắn cục bộ.
  final List<ChatMessage> _demoMessages = [];
  final List<ChatMessage> _localApiMessages = [];
  Timer? _pollTimer;
  Object? _pollError;
  int _pollFailStreak = 0;
  int _lastStaffMsgCount = 0;

  bool get _demo =>
      DemoReportConfig.enabled && AppRuntimeConfig.useStaticDemo;
  bool get _localApi => AppRuntimeConfig.useLocalApi;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _tts ??= context.read<TtsService>();
  }

  @override
  void initState() {
    super.initState();
    _abbrev = abbreviateDepartmentName(widget.departmentTitle);
    _gradient = departmentAvatarGradient(widget.departmentTitle);
    _departmentId = DepartmentCatalog.idForTitle(widget.departmentTitle);

    if (_demo) {
      _demoMessages.addAll(
        DemoDepartmentChats.messagesFor(widget.departmentTitle),
      );
      _threadId = 'demo';
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollDown());
      return;
    }

    if (_localApi) {
      if (_departmentId == null) {
        _initError =
            'Không map được phòng ban "${widget.departmentTitle}".';
        return;
      }
      _threadId = _departmentId;
      _startLocalPolling();
      return;
    }

    if (_departmentId == null) {
      _initError =
          'Không map được phòng ban "${widget.departmentTitle}" — cập nhật DepartmentCatalog.';
      return;
    }
    if (Firebase.apps.isEmpty) {
      _initError = 'Chưa cấu hình Firebase.';
      return;
    }
    DepartmentChatRepository.ensureThread(
      departmentId: _departmentId!,
      departmentTitle: widget.departmentTitle,
    ).then((id) {
      if (mounted) setState(() => _threadId = id);
    }).catchError((e) {
      if (mounted) setState(() => _initError = e);
    });
  }

  void _startLocalPolling() {
    _pollTimer?.cancel();
    _refreshLocalMessages();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 800), (_) {
      _refreshLocalMessages();
    });
  }

  Future<void> _refreshLocalMessages() async {
    if (_departmentId == null || !mounted) return;
    try {
      final rows =
          await LocalDepartmentChatRepository.fetchMessages(_departmentId!);
      final msgs = rows
          .map(
            (m) => ChatMessage(
              id: m.id,
              text: m.text,
              role: m.senderRole == 'staff'
                  ? MessageRole.assistant
                  : MessageRole.user,
              createdAt: m.createdAt ?? DateTime.now(),
            ),
          )
          .toList();
      if (!mounted) return;
      final staffCount =
          msgs.where((m) => m.role == MessageRole.assistant).length;
      setState(() {
        _localApiMessages
          ..clear()
          ..addAll(msgs);
        _pollError = null;
        _pollFailStreak = 0;
        _lastStaffMsgCount = staffCount;
      });
      _scrollDown();
      await StudentAlertService.instance.refresh();
    } catch (e) {
      if (!mounted) return;
      _pollFailStreak++;
      if (_pollFailStreak >= 3) {
        setState(() => _pollError = e);
      }
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _tts?.stop();
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOut,
        );
      }
    });
  }

  ChatMessage _docToMessage(QueryDocumentSnapshot<Map<String, dynamic>> d) {
    final m = d.data();
    final text = (m['text'] as String?) ?? '';
    final roleStr = m['senderRole'] as String? ?? 'student';
    final role =
        roleStr == 'staff' ? MessageRole.assistant : MessageRole.user;
    final ts = m['createdAt'];
    DateTime at;
    if (ts is Timestamp) {
      at = ts.toDate();
    } else {
      at = DateTime.now();
    }
    return ChatMessage(
      id: d.id,
      text: text,
      role: role,
      createdAt: at,
    );
  }

  Future<void> _onSend() async {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty || _sending || _threadId == null) return;
    _inputCtrl.clear();

    if (_demo) {
      setState(() {
        _demoMessages.add(
          ChatMessage(
            id: 'demo_local_${_demoMessages.length}',
            text: text,
            role: MessageRole.user,
            createdAt: DateTime.now(),
          ),
        );
      });
      _scrollDown();
      return;
    }

    if (_localApi) {
      setState(() => _sending = true);
      try {
        await LocalDepartmentChatRepository.sendMessage(
          departmentId: _departmentId!,
          text: text,
        );
        await _refreshLocalMessages();
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Không gửi được: $e'),
            backgroundColor: AppTheme.accentRed,
          ),
        );
      } finally {
        if (mounted) setState(() => _sending = false);
      }
      return;
    }

    setState(() => _sending = true);
    try {
      await DepartmentChatRepository.sendStudentMessage(
        threadId: _threadId!,
        text: text,
      );
      _scrollDown();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Không gửi được: $e'),
          backgroundColor: AppTheme.accentRed,
        ),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: Text(
          widget.departmentTitle,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        actions: const [NotificationBellButton()],
      ),
      body: _buildBody(),
      bottomNavigationBar: _threadId != null && _initError == null
          ? BottomInputBar(
              controller: _inputCtrl,
              enabled: !_sending,
              inputHint: 'Nhập tin nhắn tới phòng ban…',
              onSend: _onSend,
            )
          : null,
    );
  }

  Widget _buildBody() {
    if (_initError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _initError.toString(),
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppTheme.accentRed),
          ),
        ),
      );
    }
    if (_threadId == null) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.accent),
      );
    }

    if (_demo) {
      return _buildDemoMessageList();
    }

    if (_localApi) {
      if (_pollError != null && _localApiMessages.isEmpty) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Không tải chat: $_pollError\nKiểm tra BFF_BASE_URL và docker compose.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppTheme.accentRed),
            ),
          ),
        );
      }
      return _buildLocalApiMessageList();
    }

    return _buildFirestoreMessages();
  }

  Widget _buildDemoMessageList() {
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollDown());
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.fromLTRB(8, 16, 8, 8),
      itemCount: _demoMessages.length,
      itemBuilder: (_, i) {
        final m = _demoMessages[i];
        return ChatMessageTile(
          message: m,
          isLast: i == _demoMessages.length - 1,
          assistantPersonaLabel: m.isAI ? widget.departmentTitle : null,
          assistantPersonaAbbrev: m.isAI ? _abbrev : null,
          assistantAvatarGradient: m.isAI ? _gradient : null,
        );
      },
    );
  }

  Widget _buildLocalApiMessageList() {
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollDown());
    if (_localApiMessages.isEmpty) {
      return ListView(
        controller: _scrollCtrl,
        padding: const EdgeInsets.all(16),
        children: [
          ChatMessageTile(
            message: ChatMessage(
              id: 'welcome',
              text: 'Xin chào, bạn đang liên hệ **${widget.departmentTitle}**.',
              role: MessageRole.assistant,
              createdAt: DateTime.now(),
            ),
            isLast: true,
            assistantPersonaLabel: widget.departmentTitle,
            assistantPersonaAbbrev: _abbrev,
            assistantAvatarGradient: _gradient,
          ),
        ],
      );
    }
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
      itemCount: _localApiMessages.length,
      itemBuilder: (_, i) {
        final m = _localApiMessages[i];
        return ChatMessageTile(
          message: m,
          isLast: i == _localApiMessages.length - 1,
          assistantPersonaLabel: m.isAI ? widget.departmentTitle : null,
          assistantPersonaAbbrev: m.isAI ? _abbrev : null,
          assistantAvatarGradient: m.isAI ? _gradient : null,
        );
      },
    );
  }

  Widget _buildFirestoreMessages() {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: DepartmentChatRepository.messagesStream(_threadId!),
      builder: (context, snap) {
        if (snap.hasError) {
          return Center(
            child: Text(
              'Lỗi: ${snap.error}',
              style: const TextStyle(color: AppTheme.accentRed),
            ),
          );
        }
        if (!snap.hasData) {
          return const Center(
            child: CircularProgressIndicator(color: AppTheme.accent),
          );
        }
        final docs = snap.data!.docs;
        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollDown());
        if (docs.isEmpty) {
          return ListView(
            controller: _scrollCtrl,
            padding: const EdgeInsets.all(16),
            children: [
              ChatMessageTile(
                message: ChatMessage(
                  id: 'welcome',
                  text:
                      'Xin chào, bạn đang liên hệ **${widget.departmentTitle}**.',
                  role: MessageRole.assistant,
                  createdAt: DateTime.now(),
                ),
                isLast: true,
                assistantPersonaLabel: widget.departmentTitle,
                assistantPersonaAbbrev: _abbrev,
                assistantAvatarGradient: _gradient,
              ),
            ],
          );
        }
        return ListView.builder(
          controller: _scrollCtrl,
          padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
          itemCount: docs.length,
          itemBuilder: (_, i) {
            final m = _docToMessage(docs[i]);
            return ChatMessageTile(
              message: m,
              isLast: i == docs.length - 1,
              assistantPersonaLabel: m.isAI ? widget.departmentTitle : null,
              assistantPersonaAbbrev: m.isAI ? _abbrev : null,
              assistantAvatarGradient: m.isAI ? _gradient : null,
            );
          },
        );
      },
    );
  }
}
