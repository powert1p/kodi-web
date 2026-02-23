import 'package:flutter/material.dart';

/// Shared answer input card used by Practice, Diagnostic, and Exam pages.
class AnswerInput extends StatelessWidget {
  const AnswerInput({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.onSubmit,
    this.onSkip,
    this.onReport,
    this.accentColor = const Color(0xFF2563EB),
    this.showHints = true,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final VoidCallback onSubmit;
  final VoidCallback? onSkip;
  final VoidCallback? onReport;
  final Color accentColor;
  final bool showHints;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.04),
          blurRadius: 6, offset: const Offset(0, 2))]),
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (showHints)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              Text('Ваш ответ',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600,
                  color: Colors.grey[600])),
              const Spacer(),
              Text('Enter — ответить',
                style: TextStyle(fontSize: 11, color: Colors.grey[400])),
            ]),
          ),
        TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            hintText: 'Введите ответ...',
            filled: true,
            fillColor: const Color(0xFFF8FAFC),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: accentColor, width: 2)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            suffixIcon: IconButton(
              icon: Icon(Icons.send_rounded, color: accentColor),
              onPressed: onSubmit)),
          style: const TextStyle(fontSize: 16),
          onSubmitted: (_) => onSubmit()),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: FilledButton(
            onPressed: onSubmit,
            style: FilledButton.styleFrom(
              minimumSize: const Size(0, 48),
              backgroundColor: accentColor),
            child: const Text('Ответить',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)))),
          if (onSkip != null) ...[
            const SizedBox(width: 10),
            SizedBox(height: 48, child: OutlinedButton(
              onPressed: onSkip,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Color(0xFFE2E8F0))),
              child: const Text('Пропустить',
                style: TextStyle(color: Color(0xFF64748B))))),
          ],
          if (onReport != null) ...[
            const SizedBox(width: 6),
            SizedBox(height: 48, child: IconButton(
              onPressed: onReport,
              icon: const Icon(Icons.flag_outlined, color: Color(0xFFCBD5E1), size: 20),
              tooltip: 'Пожаловаться')),
          ],
        ]),
      ]));
  }
}
