import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../../app/colors.dart';
import '../../../../shared/utils/responsive.dart';

class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.student, required this.stats});
  final Student student;
  final Stats stats;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    final pct = stats.masteryPercent;
    final firstName = student.displayName.split(' ').first;
    final dayWord = stats.currentStreak == 1
        ? l.day1
        : stats.currentStreak < 5
            ? l.day2to4
            : l.day5plus;
    return Container(
      padding: EdgeInsets.all(rp(context, 24)),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
            colors: [AppColors.heroGradientStart, AppColors.heroGradientEnd],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(children: [
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    l.heroHello(firstName),
                    style: TextStyle(
                        color: Colors.white70, fontSize: rs(context, 15))),
                const SizedBox(height: 4),
                Text(l.yourProgress,
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: rs(context, 22),
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Text(
                    l.topicsMastered(stats.masteredCount, stats.totalNodes),
                    style: const TextStyle(
                        color: Colors.white70, fontSize: 14)),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: pct,
                    minHeight: 10,
                    backgroundColor: Colors.white.withValues(alpha: 0.2),
                    valueColor:
                        const AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                ),
                if (stats.currentStreak > 0) ...[
                  const SizedBox(height: 10),
                  Row(children: [
                    const Text('🔥', style: TextStyle(fontSize: 16)),
                    const SizedBox(width: 4),
                    Text(
                      l.streakDays(stats.currentStreak, dayWord),
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ]),
                ],
              ]),
        ),
        const SizedBox(width: 20),
        RingChart(percent: pct),
      ]),
    );
  }
}

class RingChart extends StatelessWidget {
  const RingChart({super.key, required this.percent});
  final double percent;
  @override
  Widget build(BuildContext context) {
    final s = rs(context, 80);
    return SizedBox(
        width: s,
        height: s,
        child: Stack(alignment: Alignment.center, children: [
          CustomPaint(
              size: Size(s, s), painter: RingPainter(percent)),
          Text('${(percent * 100).toStringAsFixed(0)}%',
              style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: rs(context, 16))),
        ]),
      );
  }
}

class RingPainter extends CustomPainter {
  const RingPainter(this.percent);
  final double percent;
  @override
  void paint(Canvas canvas, Size size) {
    final bg = Paint()
      ..color = Colors.white.withValues(alpha: 0.2)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke;
    final fg = Paint()
      ..color = Colors.white
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - 8) / 2;
    canvas.drawCircle(center, radius, bg);
    canvas.drawArc(Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2, 2 * math.pi * percent, false, fg);
  }

  @override
  bool shouldRepaint(RingPainter old) => old.percent != percent;
}
