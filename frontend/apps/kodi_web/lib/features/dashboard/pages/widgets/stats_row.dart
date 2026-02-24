import 'package:flutter/material.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../../app/colors.dart';
import '../../../../shared/utils/responsive.dart';

class StatsRow extends StatelessWidget {
  const StatsRow({super.key, required this.stats});
  final Stats stats;
  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final cardWidth = (w < 400) ? (w - 50) / 2 : 140.0;
    return Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          SizedBox(width: cardWidth, child: StatCard(
              label: 'Освоено',
              value: '${stats.masteredCount}/${stats.totalNodes}',
              icon: Icons.school_rounded,
              color: AppColors.success)),
          SizedBox(width: cardWidth, child: StatCard(
              label: 'Решено',
              value: '${stats.solved}',
              icon: Icons.check_circle_outline,
              color: AppColors.primary)),
          SizedBox(width: cardWidth, child: StatCard(
              label: 'Точность',
              value: '${stats.accuracy}%',
              icon: Icons.analytics_outlined,
              color: AppColors.warning)),
          SizedBox(width: cardWidth, child: StatCard(
              label: 'Ср. время',
              value: '${stats.avgTimeS.toStringAsFixed(0)}с',
              icon: Icons.timer_outlined,
              color: AppColors.purpleLight)),
        ],
      );
  }
}

class StatCard extends StatelessWidget {
  const StatCard(
      {super.key,
      required this.label,
      required this.value,
      required this.icon,
      required this.color});
  final String label, value;
  final IconData icon;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.all(rp(context, 14)),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 6,
                  offset: const Offset(0, 2))
            ]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
              width: rs(context, 36),
              height: rs(context, 36),
              decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, color: color, size: rs(context, 20))),
          const SizedBox(height: 10),
          Text(value,
              style: TextStyle(
                  fontSize: rs(context, 18),
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary)),
          Text(label,
              style: TextStyle(
                  fontSize: rs(context, 11),
                  color: AppColors.textSecondary)),
        ]),
      );
}
