import 'package:flutter/material.dart';
import 'math_text.dart';

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
      // Topic + difficulty + counter row
      Row(children: [
        if (nodeName != null && nodeName!.isNotEmpty)
          Expanded(child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(8)),
            child: Text(nodeName!,
              style: const TextStyle(color: Color(0xFF2563EB),
                fontWeight: FontWeight.w600, fontSize: 13),
              overflow: TextOverflow.ellipsis))),
        if (difficulty != null) ...[
          const SizedBox(width: 8),
          _DifficultyDots(level: difficulty!),
        ],
        if (counter != null) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(20)),
            child: Text(counter!,
              style: TextStyle(color: Colors.grey[600],
                fontSize: 13, fontWeight: FontWeight.w600))),
        ],
      ]),
      const SizedBox(height: 12),

      // Card with text
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 8, offset: const Offset(0, 2))]),
        child: MathText(text,
          style: const TextStyle(
            fontSize: 17, height: 1.6, color: Color(0xFF1E293B))),
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
