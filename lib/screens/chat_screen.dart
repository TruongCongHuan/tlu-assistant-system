// lib/screens/chat_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../providers/chat_provider.dart';
import '../services/tts_service.dart';
import '../widgets/bottom_input_bar.dart';
import '../widgets/chat_message_tile.dart';
import '../widgets/notification_bell_button.dart';
import 'pdf_manager_screen.dart';

class ChatScreen extends StatefulWidget {
  /// Nếu null hoặc rỗng: mở chat trống, chờ người dùng nhập ở thanh dưới.
  final String? initialMessage;

  const ChatScreen({super.key, this.initialMessage});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  late final ChatProvider _chat;

  bool get _expectInitial =>
      widget.initialMessage != null &&
      widget.initialMessage!.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    _chat = context.read<ChatProvider>();
    _chat.addListener(_onChatUpdate);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final initial = widget.initialMessage?.trim();
      if (initial != null && initial.isNotEmpty) {
        _chat.sendMessage(initial);
      }
    });
  }

  void _onChatUpdate() => _scrollToBottom();

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    context.read<TtsService>().stop();
    _chat.removeListener(_onChatUpdate);
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();
    final msgs = chat.messages;

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: const Text('TLU AI Assistant'),
        actions: [
          if (chat.activeDocId != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Chip(
                label: const Text('Doc', style: TextStyle(fontSize: 11)),
                backgroundColor: AppTheme.accent.withOpacity(0.15),
                side: BorderSide(color: AppTheme.accent.withOpacity(0.3)),
                padding: EdgeInsets.zero,
                labelPadding: const EdgeInsets.symmetric(horizontal: 8),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.description_outlined),
            color: AppTheme.textSecondary,
            tooltip: 'Quản lý tài liệu',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PdfManagerScreen()),
            ),
          ),
          const NotificationBellButton(),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert, color: AppTheme.textSecondary),
            color: AppTheme.surfaceHigh,
            itemBuilder: (_) => [
              const PopupMenuItem(
                value: 'clear',
                child: Text('Xóa cuộc trò chuyện',
                    style: TextStyle(color: AppTheme.textPrimary)),
              ),
              const PopupMenuItem(
                value: 'all_docs',
                child: Text('Tìm trong tất cả tài liệu',
                    style: TextStyle(color: AppTheme.textPrimary)),
              ),
            ],
            onSelected: (v) {
              if (v == 'clear') chat.clearMessages();
              if (v == 'all_docs') chat.setActiveDoc(null);
            },
          ),
        ],
      ),
      body: msgs.isEmpty && !chat.isThinking && !_expectInitial
          ? const _WelcomeChatEmpty()
          : msgs.isEmpty && (chat.isThinking || _expectInitial)
              ? const _EmptyState()
              : ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.fromLTRB(8, 16, 8, 8),
                  itemCount: msgs.length,
                  itemBuilder: (_, i) => ChatMessageTile(
                    message: msgs[i],
                    isLast: i == msgs.length - 1,
                  ),
                ),
      bottomNavigationBar: BottomInputBar(
        controller: _inputCtrl,
        enabled: !chat.isThinking,
        onSend: () {
          final text = _inputCtrl.text.trim();
          if (text.isEmpty) return;
          _inputCtrl.clear();
          chat.sendMessage(text);
        },
        onAttachPdf: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const PdfManagerScreen()),
        ),
      ),
    );
  }
}

class _WelcomeChatEmpty extends StatelessWidget {
  const _WelcomeChatEmpty();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.chat_bubble_outline_rounded,
                size: 56, color: AppTheme.textTertiary.withOpacity(0.8)),
            const SizedBox(height: 16),
            const Text(
              'Nhập câu hỏi ở thanh bên dưới để bắt đầu trò chuyện với TLU AI.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 15,
                height: 1.45,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(
        strokeWidth: 2,
        color: AppTheme.accent,
      ),
    );
  }
}
