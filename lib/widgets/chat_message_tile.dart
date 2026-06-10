// lib/widgets/chat_message_tile.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../models/conversation.dart';
import '../models/rag_stream.dart';
import '../providers/chat_provider.dart';
import '../services/tts_service.dart';
import '../theme/app_theme.dart';

class ChatMessageTile extends StatelessWidget {
  final ChatMessage message;
  final bool isLast;

  /// Chat với phòng ban: tên hiển thị cạnh avatar (thay cho "TLU AI").
  final String? assistantPersonaLabel;

  /// 1–2 ký tự trên avatar phía phòng ban / cố vấn.
  final String? assistantPersonaAbbrev;

  /// Màu nền avatar (gradient 2 màu). Mặc định gradient TLU AI.
  final List<Color>? assistantAvatarGradient;

  const ChatMessageTile({
    super.key,
    required this.message,
    this.isLast = false,
    this.assistantPersonaLabel,
    this.assistantPersonaAbbrev,
    this.assistantAvatarGradient,
  });

  bool get _staffPersona =>
      assistantPersonaLabel != null && assistantPersonaLabel!.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    if (message.isUser) {
      return _UserBubble(message: message);
    }
    return _AiBubble(
      message: message,
      isLast: isLast,
      personaLabel: assistantPersonaLabel?.trim(),
      personaAbbrev: assistantPersonaAbbrev?.trim(),
      personaGradient: assistantAvatarGradient,
      showAssistantActions: !_staffPersona,
    );
  }
}

// ── User Bubble ────────────────────────────────────────
class _UserBubble extends StatelessWidget {
  final ChatMessage message;
  const _UserBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16, left: 32),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.userBubble,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(20),
                  topRight: Radius.circular(20),
                  bottomLeft: Radius.circular(20),
                  bottomRight: Radius.circular(4),
                ),
                border: Border.all(
                  color: AppTheme.accent.withOpacity(0.2),
                ),
              ),
              child: Text(
                message.text,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 16,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 200.ms)
        .slideX(begin: 0.1, end: 0, duration: 250.ms);
  }
}

// ── AI Bubble ──────────────────────────────────────────
class _AiBubble extends StatelessWidget {
  final ChatMessage message;
  final bool isLast;
  final String? personaLabel;
  final String? personaAbbrev;
  final List<Color>? personaGradient;
  final bool showAssistantActions;

  const _AiBubble({
    required this.message,
    required this.isLast,
    this.personaLabel,
    this.personaAbbrev,
    this.personaGradient,
    this.showAssistantActions = true,
  });

  @override
  Widget build(BuildContext context) {
    final tts = context.watch<TtsService>();
    final isSending = message.status == MessageStatus.sending;
    final isThisMsgPlaying = tts.playingId == message.id;
    final displayName = (personaLabel != null && personaLabel!.isNotEmpty)
        ? personaLabel!
        : 'TLU AI';
    final abbrev = (personaAbbrev != null && personaAbbrev!.isNotEmpty)
        ? personaAbbrev!.characters.take(2).toString()
        : 'T';
    final gradient = personaGradient != null && personaGradient!.length >= 2
        ? personaGradient!
        : const [Color(0xFF4285F4), Color(0xFF9C27B0)];

    return Padding(
      padding: const EdgeInsets.only(bottom: 20, left: 8, right: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _AiAvatar(abbrev: abbrev, gradientColors: gradient),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  displayName,
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // ── Content ───────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isSending && message.text.isEmpty)
                  _TypingDots()
                else
                  MarkdownBody(
                    data: message.text,
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      p: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        height: 1.6,
                      ),
                      strong: const TextStyle(
                        color: AppTheme.accent,
                        fontWeight: FontWeight.bold,
                      ),
                      listBullet: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                      ),
                    ),
                  ),

                if (showAssistantActions &&
                    !isSending &&
                    message.text.isNotEmpty)
                  _ActionRow(
                    message: message,
                    tts: tts,
                    isPlaying: isThisMsgPlaying,
                    onRate: (rating) {
                      context.read<ChatProvider>().rateRagMessage(
                            message.id,
                            rating,
                          );
                    },
                  ),
              ],
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 250.ms)
        .slideY(begin: 0.05, end: 0, duration: 300.ms);
  }
}

class _AiAvatar extends StatelessWidget {
  final String abbrev;
  final List<Color> gradientColors;

  const _AiAvatar({
    this.abbrev = 'T',
    this.gradientColors = const [Color(0xFF4285F4), Color(0xFF9C27B0)],
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: gradientColors,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Center(
        child: Text(
          abbrev,
          style: TextStyle(
            color: Colors.white,
            fontSize: abbrev.characters.length > 1 ? 10 : 14,
            fontWeight: FontWeight.bold,
            height: 1,
          ),
          maxLines: 1,
        ),
      ),
    );
  }
}

// ── Action buttons below AI message ───────────────────
class _ActionRow extends StatelessWidget {
  final ChatMessage message;
  final TtsService tts;
  final bool isPlaying;
  final void Function(RagMessageRating rating)? onRate;

  const _ActionRow({
    required this.message,
    required this.tts,
    required this.isPlaying,
    this.onRate,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        children: [
          if (onRate != null) ...[
            _SmallBtn(
              icon: Icons.thumb_up_outlined,
              tooltip: 'Hữu ích',
              active: message.ragRating == RagMessageRating.up,
              onTap: () => onRate!(RagMessageRating.up),
            ),
            const SizedBox(width: 4),
            _SmallBtn(
              icon: Icons.thumb_down_outlined,
              tooltip: 'Chưa hữu ích',
              active: message.ragRating == RagMessageRating.down,
              onTap: () => onRate!(RagMessageRating.down),
            ),
            const SizedBox(width: 8),
          ],
          // Copy
          _SmallBtn(
            icon: Icons.copy_rounded,
            tooltip: 'Sao chép',
            onTap: () {
              Clipboard.setData(ClipboardData(text: message.text));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Đã sao chép'),
                  duration: Duration(seconds: 1),
                  behavior: SnackBarBehavior.floating,
                ),
              );
            },
          ),
          const SizedBox(width: 4),

          // TTS play/stop
          _SmallBtn(
            icon: isPlaying
                ? Icons.stop_circle_outlined
                : Icons.volume_up_outlined,
            tooltip: isPlaying ? 'Dừng đọc' : 'Đọc to',
            active: isPlaying,
            onTap: () => tts.speak(message.text, messageId: message.id),
          ),
        ],
      ),
    );
  }
}

class _SmallBtn extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  final bool active;

  const _SmallBtn({
    required this.icon,
    required this.tooltip,
    required this.onTap,
    this.active = false,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(
            icon,
            size: 18,
            color: active ? AppTheme.accent : AppTheme.textTertiary,
          ),
        ),
      ),
    );
  }
}

// ── Typing dots animation ──────────────────────────────
class _TypingDots extends StatefulWidget {
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with TickerProviderStateMixin {
  late List<AnimationController> _ctrls;

  @override
  void initState() {
    super.initState();
    _ctrls = List.generate(3, (i) {
      final c = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 500),
      );
      Future.delayed(Duration(milliseconds: i * 150), () {
        if (mounted) c.repeat(reverse: true);
      });
      return c;
    });
  }

  @override
  void dispose() {
    for (final c in _ctrls) c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) {
        return AnimatedBuilder(
          animation: _ctrls[i],
          builder: (_, __) => Container(
            width: 8,
            height: 8 + _ctrls[i].value * 8,
            margin: const EdgeInsets.only(right: 4),
            decoration: BoxDecoration(
              color: AppTheme.accent.withOpacity(0.5 + _ctrls[i].value * 0.5),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        );
      }),
    );
  }
}
