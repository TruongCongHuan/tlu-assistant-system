// lib/widgets/quick_action_chip.dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class QuickActionChip extends StatefulWidget {
  final String emoji;
  final String label;
  final VoidCallback onTap;

  const QuickActionChip({
    super.key,
    required this.emoji,
    required this.label,
    required this.onTap,
  });

  @override
  State<QuickActionChip> createState() => _QuickActionChipState();
}

class _QuickActionChipState extends State<QuickActionChip> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 100),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
        decoration: BoxDecoration(
          color: _pressed
              ? AppTheme.surfaceHigh
              : AppTheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppTheme.surfaceBorder),
        ),
        child: Row(
          children: [
            Text(widget.emoji, style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                widget.label,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
