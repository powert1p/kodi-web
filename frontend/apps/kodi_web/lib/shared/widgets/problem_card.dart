import 'package:flutter/material.dart';
import 'math_text.dart';
import '../utils/responsive.dart';

/// Shared problem display card used by Practice, Diagnostic, and Exam pages.
/// Shows text always via MathText. No dark images.
class ProblemCard extends StatelessWidget {
  const ProblemCard({
    super.key,
    required this.text,
    this.nodeName,
    this.difficulty,
    this.counter,
  });

  final String text;
  final String? nodeName;
  final int? difficulty;
  final String? counter;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        if (nodeName != null && nodeName!.isNotEmpty)
          Flexible(child: Container(
            padding: EdgeInsets.symmetric(horizontal: rp(context, 12), vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(8)),
            child: Text(nodeName!,
              style: TextStyle(color: const Color(0xFF2563EB),
                fontWeight: FontWeight.w600, fontSize: rs(context, 13)),
              overflow: TextOverflow.ellipsis))),
        if (difficulty != null) ...[
          const SizedBox(width: 8),
          _DifficultyDots(level: difficulty!),
        ],
        if (counter != null) ...[
          const SizedBox(width: 8),
          Container(
            padding: EdgeInsets.symmetric(horizontal: rp(context, 10), vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(20)),
            child: Text(counter!,
              style: TextStyle(color: Colors.grey[600],
                fontSize: rs(context, 13), fontWeight: FontWeight.w600))),
        ],
      ]),
      const SizedBox(height: 12),

      Container(
        width: double.infinity,
        padding: EdgeInsets.all(rp(context, 20)),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 8, offset: const Offset(0, 2))]),
        child: MathText(text,
          style: TextStyle(
            fontSize: rs(context, 17), height: 1.6, color: const Color(0xFF1E293B))),
      ),
    ]);
  }
}

class _DifficultyDots extends StatelessWidget {
  const _DifficultyDots({required this.level});
  final int level;
  @override
  Widget build(BuildContext context) => Row(
    children: List.generate(4, (i) => Container(
      width: 8, height: 8, margin: const EdgeInsets.only(right: 3),
      decoration: BoxDecoration(shape: BoxShape.circle,
        color: i < level ? const Color(0xFF2563EB) : const Color(0xFFE2E8F0)))));
}
