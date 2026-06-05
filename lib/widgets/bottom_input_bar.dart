// lib/widgets/bottom_input_bar.dart
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../services/stt_service.dart';

class BottomInputBar extends StatefulWidget {
  final TextEditingController controller;
  final VoidCallback onSend;
  final VoidCallback? onAttachPdf;
  final bool enabled;
  /// Gợi ý trong ô nhập (mặc định cho TLU AI).
  final String? inputHint;

  const BottomInputBar({
    super.key,
    required this.controller,
    required this.onSend,
    this.onAttachPdf,
    this.enabled = true,
    this.inputHint,
  });

  @override
  State<BottomInputBar> createState() => _BottomInputBarState();
}

class _BottomInputBarState extends State<BottomInputBar>
    with TickerProviderStateMixin {
  late AnimationController _pulseCtrl;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    widget.controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final has = widget.controller.text.isNotEmpty;
    if (has != _hasText) {
      setState(() => _hasText = has);
    }
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final stt    = context.watch<SttService>();
    final bottom = MediaQuery.of(context).padding.bottom;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border(
          top: BorderSide(
            color: stt.isListening
                ? AppTheme.accentRed.withOpacity(0.4)
                : AppTheme.surfaceBorder,
            width: stt.isListening ? 1.5 : 0.5,
          ),
        ),
      ),
      padding: EdgeInsets.fromLTRB(16, 12, 16, bottom + 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // ── STT Overlay (khi đang nghe) ────────────────
          if (stt.isListening || stt.state == SttState.processing)
            _SttOverlay(stt: stt)
                .animate()
                .fadeIn(duration: 200.ms)
                .slideY(begin: 0.2, end: 0),

          // ── Text Field ─────────────────────────────────
          if (!stt.isListening)
            TextField(
              controller: widget.controller,
              enabled: widget.enabled && !stt.isListening,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 15,
                height: 1.5,
              ),
              maxLines: 5,
              minLines: 1,
              decoration: InputDecoration(
                hintText: widget.inputHint ?? 'Hỏi TLU AI…',
                hintStyle: const TextStyle(color: AppTheme.textTertiary),
                border: InputBorder.none,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
              ),
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => widget.onSend(),
            ),

          const SizedBox(height: 8),

          // ── Action Row ─────────────────────────────────
          Row(
            children: [
              if (widget.onAttachPdf != null) ...[
                _ActionBtn(
                  icon: Icons.attach_file_rounded,
                  tooltip: 'Thêm tài liệu',
                  onTap: widget.onAttachPdf!,
                ),
                const SizedBox(width: 4),
              ],

              const Spacer(),

              // "Flash" mode chip
              _FlashChip(),
              const SizedBox(width: 8),

              // Mic / Waveform button
              _MicButton(
                stt: stt,
                onTextPartial: (t) => widget.controller.text = t,
                onTextFinal: (t) {
                  widget.controller.text = t;
                  if (t.isNotEmpty) widget.onSend();
                },
              ),
              const SizedBox(width: 8),

              // Send button
              _SendButton(
                hasText: _hasText,
                enabled: widget.enabled && !stt.isListening,
                onTap: widget.onSend,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Mic Button với waveform animation ─────────────────
class _MicButton extends StatefulWidget {
  final SttService stt;
  final void Function(String) onTextPartial;
  final void Function(String) onTextFinal;

  const _MicButton({
    required this.stt,
    required this.onTextPartial,
    required this.onTextFinal,
  });

  @override
  State<_MicButton> createState() => _MicButtonState();
}

class _MicButtonState extends State<_MicButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _rippleCtrl;

  @override
  void initState() {
    super.initState();
    _rippleCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    widget.stt.addListener(_onSttChange);
  }

  void _onSttChange() {
    if (widget.stt.isListening) {
      _rippleCtrl.repeat();
    } else {
      _rippleCtrl.stop();
      _rippleCtrl.reset();
    }
  }

  @override
  void dispose() {
    _rippleCtrl.dispose();
    widget.stt.removeListener(_onSttChange);
    super.dispose();
  }

  Future<void> _toggle() async {
    if (widget.stt.isListening) {
      await widget.stt.stop();
    } else {
      await widget.stt.startListening(
        onResult: widget.onTextPartial,
        onFinal: widget.onTextFinal,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isListening = widget.stt.isListening;
    final level       = widget.stt.soundLevel;

    return GestureDetector(
      onTap: _toggle,
      child: AnimatedBuilder(
        animation: _rippleCtrl,
        builder: (_, child) {
          return SizedBox(
            width: 44,
            height: 44,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Ripple ring khi đang nghe
                if (isListening)
                  ...[1.0, 0.6, 0.3].map((opacity) {
                    final scale = 1.0 +
                        (_rippleCtrl.value + (1 - opacity)) % 1.0 * 0.8 +
                        level * 0.4;
                    return Transform.scale(
                      scale: scale,
                      child: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppTheme.accentRed.withOpacity(
                              opacity * (1 - _rippleCtrl.value * 0.5),
                            ),
                            width: 1.5,
                          ),
                        ),
                      ),
                    );
                  }),

                // Button core
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isListening
                        ? AppTheme.accentRed
                        : Colors.transparent,
                  ),
                  child: Icon(
                    isListening ? Icons.stop_rounded : Icons.mic_none_rounded,
                    color: isListening
                        ? Colors.white
                        : AppTheme.textSecondary,
                    size: 22,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ── STT Overlay (live transcription display) ──────────
class _SttOverlay extends StatelessWidget {
  final SttService stt;
  const _SttOverlay({required this.stt});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      child: Column(
        children: [
          // Waveform bars
          _WaveformBars(level: stt.soundLevel),
          const SizedBox(height: 10),

          // Live text
          Text(
            stt.currentWords.isEmpty
                ? (stt.state == SttState.processing
                    ? 'Đang xử lý…'
                    : 'Đang lắng nghe…')
                : stt.currentWords,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: stt.currentWords.isEmpty
                  ? AppTheme.textTertiary
                  : AppTheme.textPrimary,
              fontSize: 15,
              fontStyle: stt.currentWords.isEmpty
                  ? FontStyle.italic
                  : FontStyle.normal,
            ),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }
}

// ── Animated waveform bars ─────────────────────────────
class _WaveformBars extends StatefulWidget {
  final double level;
  const _WaveformBars({required this.level});

  @override
  State<_WaveformBars> createState() => _WaveformBarsState();
}

class _WaveformBarsState extends State<_WaveformBars>
    with TickerProviderStateMixin {
  static const int _barCount = 5;
  late List<AnimationController> _controllers;
  final _rng = Random();

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(_barCount, (i) {
      final c = AnimationController(
        vsync: this,
        duration: Duration(milliseconds: 300 + _rng.nextInt(300)),
      );
      Future.delayed(Duration(milliseconds: i * 80), () {
        if (mounted) c.repeat(reverse: true);
      });
      return c;
    });
  }

  @override
  void dispose() {
    for (final c in _controllers) c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 32,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: List.generate(_barCount, (i) {
          return AnimatedBuilder(
            animation: _controllers[i],
            builder: (_, __) {
              final minH = 4.0;
              final maxH = 8.0 + widget.level * 24;
              final h    = minH + _controllers[i].value * (maxH - minH);
              return Container(
                width: 4,
                height: h,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                decoration: BoxDecoration(
                  color: AppTheme.accentRed,
                  borderRadius: BorderRadius.circular(2),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}

// ── Send button ────────────────────────────────────────
class _SendButton extends StatelessWidget {
  final bool hasText;
  final bool enabled;
  final VoidCallback onTap;

  const _SendButton({
    required this.hasText,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled && hasText ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: hasText && enabled
              ? AppTheme.accent
              : AppTheme.surfaceHigh,
        ),
        child: Icon(
          Icons.arrow_upward_rounded,
          color: hasText && enabled
              ? AppTheme.background
              : AppTheme.textTertiary,
          size: 20,
        ),
      ),
    );
  }
}

// ── Flash chip ─────────────────────────────────────────
class _FlashChip extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: AppTheme.surfaceHigh,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.surfaceBorder),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt_rounded, color: AppTheme.accent, size: 15),
          SizedBox(width: 4),
          Text(
            'Flash',
            style: TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _ActionBtn({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: IconButton(
        onPressed: onTap,
        icon: Icon(icon, color: AppTheme.textSecondary, size: 22),
        padding: EdgeInsets.zero,
        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
      ),
    );
  }
}
