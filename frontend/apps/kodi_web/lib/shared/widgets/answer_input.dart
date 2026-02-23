import 'package:flutter/material.dart';
import '../utils/responsive.dart';

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
      padding: EdgeInsets.all(rp(context, 16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (showHints)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              Text('Ваш ответ',
                style: TextStyle(fontSize: rs(context, 13), fontWeight: FontWeight.w600,
                  color: Colors.grey[600])),
              const Spacer(),
              Text('Enter — ответить',
                style: TextStyle(fontSize: rs(context, 11), color: Colors.grey[400])),
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
            contentPadding: EdgeInsets.symmetric(horizontal: rp(context, 16), vertical: 14),
            suffixIcon: IconButton(
              icon: Icon(Icons.send_rounded, color: accentColor),
              onPressed: onSubmit)),
          style: TextStyle(fontSize: rs(context, 16)),
          onSubmitted: (_) => onSubmit()),
        const SizedBox(height: 12),
        LayoutBuilder(builder: (context, constraints) {
          final narrow = constraints.maxWidth < 320;
          final btnHeight = rs(context, 48);
          final children = <Widget>[
            Expanded(child: FilledButton(
              onPressed: onSubmit,
              style: FilledButton.styleFrom(
                minimumSize: Size(0, btnHeight),
                backgroundColor: accentColor),
              child: Text('Ответить',
                style: TextStyle(fontSize: rs(context, 15), fontWeight: FontWeight.w600)))),
            if (onSkip != null) ...[
              SizedBox(width: narrow ? 6 : 10),
              SizedBox(height: btnHeight, child: OutlinedButton(
                onPressed: onSkip,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFFE2E8F0)),
                  padding: EdgeInsets.symmetric(horizontal: rp(context, 16))),
                child: Text('Пропустить',
                  style: TextStyle(color: const Color(0xFF64748B), fontSize: rs(context, 14))))),
            ],
            if (onReport != null) ...[
              const SizedBox(width: 6),
              SizedBox(height: btnHeight, child: IconButton(
                onPressed: onReport,
                icon: Icon(Icons.flag_outlined, color: const Color(0xFFCBD5E1), size: rs(context, 20)),
                tooltip: 'Пожаловаться')),
            ],
          ];
          return Row(children: children);
        }),
      ]));
  }
}
