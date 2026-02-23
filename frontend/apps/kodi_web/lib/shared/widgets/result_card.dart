import 'package:flutter/material.dart';
import 'math_text.dart';
import '../utils/responsive.dart';

/// Shared answer result display used across Practice, Diagnostic, Exam.
class ResultCard extends StatelessWidget {
  const ResultCard({
    super.key,
    required this.isCorrect,
    this.correctAnswer,
    this.solution,
    this.pMastery,
    this.isMastered = false,
    this.nodeName,
    this.onReport,
  });

  final bool isCorrect;
  final String? correctAnswer;
  final String? solution;
  final double? pMastery;
  final bool isMastered;
  final String? nodeName;
  final VoidCallback? onReport;

  @override
  Widget build(BuildContext context) {
    final ok = isCorrect;
    return Container(
      padding: EdgeInsets.all(rp(context, 20)),
      decoration: BoxDecoration(
        color: ok ? const Color(0xFFECFDF5) : const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: ok ? const Color(0xFF10B981) : const Color(0xFFEF4444),
          width: 1.5)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(ok ? Icons.check_circle_rounded : Icons.cancel_rounded,
            color: ok ? const Color(0xFF10B981) : const Color(0xFFEF4444), size: rs(context, 24)),
          const SizedBox(width: 8),
          Flexible(child: Text(ok ? 'Правильно! 🎉' : 'Неправильно',
            style: TextStyle(fontSize: rs(context, 17), fontWeight: FontWeight.bold,
              color: ok ? const Color(0xFF10B981) : const Color(0xFFEF4444)),
            overflow: TextOverflow.ellipsis)),
          const Spacer(),
          if (isMastered)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981),
                borderRadius: BorderRadius.circular(20)),
              child: Text('✨ Освоено',
                style: TextStyle(color: Colors.white, fontSize: rs(context, 11), fontWeight: FontWeight.w600))),
          if (onReport != null && !ok)
            IconButton(
              onPressed: onReport,
              icon: Icon(Icons.flag_outlined, size: rs(context, 18)),
              color: Colors.grey[400],
              tooltip: 'Пожаловаться',
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32)),
        ]),

        // Topic name
        if (nodeName != null && nodeName!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(nodeName!,
            style: TextStyle(fontSize: 12, color: Colors.grey[500])),
        ],

        // Correct answer
        if (!ok && correctAnswer != null && correctAnswer!.isNotEmpty) ...[
          const SizedBox(height: 12),
          Container(
            padding: EdgeInsets.all(rp(context, 12)),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10)),
            child: Row(children: [
              Text('Ответ: ', style: TextStyle(color: Colors.grey[500], fontSize: rs(context, 14))),
              Expanded(child: MathText(correctAnswer!,
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: rs(context, 16), color: const Color(0xFF1E293B)))),
            ])),
        ],

        if (solution != null && solution!.isNotEmpty) ...[
          const SizedBox(height: 14),
          Container(
            padding: EdgeInsets.all(rp(context, 14)),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(10)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('💡 Решение:',
                style: TextStyle(fontWeight: FontWeight.w600, color: const Color(0xFF1E293B), fontSize: rs(context, 14))),
              const SizedBox(height: 6),
              MathText(solution!,
                style: TextStyle(color: const Color(0xFF475569), height: 1.5, fontSize: rs(context, 14))),
            ])),
        ],

        // Mastery bar
        if (pMastery != null) ...[
          const SizedBox(height: 14),
          Row(children: [
            Text('Освоение: ',
              style: TextStyle(color: Colors.grey[500], fontSize: 13)),
            Expanded(child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: pMastery!,
                minHeight: 8,
                backgroundColor: const Color(0xFFE2E8F0),
                valueColor: AlwaysStoppedAnimation<Color>(
                  pMastery! >= 0.7 ? const Color(0xFF10B981)
                    : pMastery! >= 0.4 ? const Color(0xFFF59E0B) : const Color(0xFF2563EB))))),
            const SizedBox(width: 8),
            Text('${(pMastery! * 100).toStringAsFixed(0)}%',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          ]),
        ],
      ]));
  }
}
