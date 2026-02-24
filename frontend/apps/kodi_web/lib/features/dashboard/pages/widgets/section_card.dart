import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../../app/colors.dart';
import '../../bloc/dashboard_bloc.dart';
import '../../../practice/pages/practice_page.dart';
import 'section_data.dart';

class SectionCard extends StatefulWidget {
  const SectionCard({super.key, required this.section});
  final SectionData section;
  @override
  State<SectionCard> createState() => _SectionCardState();
}

class _SectionCardState extends State<SectionCard>
    with SingleTickerProviderStateMixin {
  bool _expanded = false;

  Color _pctColor(int pct) {
    if (pct >= 75) return AppColors.progressGreen;
    if (pct >= 60) return AppColors.progressOrange;
    return AppColors.progressRed;
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.section;
    final pctColor = s.testedCount > 0
        ? _pctColor(s.percentage)
        : Colors.grey[400]!;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 6,
              offset: const Offset(0, 2)),
        ],
      ),
      child: Column(
        children: [
          // -- Header (tappable) --
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Column(
                children: [
                  Row(
                    children: [
                      // Icon
                      Text(s.icon, style: const TextStyle(fontSize: 28)),
                      const SizedBox(width: 12),
                      // Name + subtitle
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    s.nameRu,
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 16),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              s.testedCount > 0
                                  ? '${s.testedCount} из ${s.totalCount} проверено'
                                  : '${s.totalCount} тем',
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey[500]),
                            ),
                          ],
                        ),
                      ),
                      // Percentage
                      if (s.testedCount > 0)
                        Text(
                          '${s.percentage}%',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: pctColor,
                          ),
                        ),
                      const SizedBox(width: 8),
                      // Arrow
                      AnimatedRotation(
                        turns: _expanded ? 0.5 : 0,
                        duration: const Duration(milliseconds: 200),
                        child: Icon(Icons.keyboard_arrow_down,
                            color: Colors.grey[400]),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  // -- 3-segment progress bar --
                  ThreeSegmentBar(
                    green: s.barGreen,
                    red: s.barRed,
                    gray: s.barGray,
                  ),
                ],
              ),
            ),
          ),
          // -- Expanded topics --
          AnimatedCrossFade(
            firstChild: const SizedBox.shrink(),
            secondChild: Column(
              children: [
                TopicsList(topics: s.topics),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                  child: SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => Navigator.of(context).pushNamed(
                        PracticePage.routeName,
                        arguments: {'tag': s.tag, 'tagName': s.nameRu},
                      ).then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                      icon: const Icon(Icons.play_arrow_rounded, size: 18),
                      label: Text('Тренировать: ${s.nameRu}',
                          style: const TextStyle(fontSize: 13)),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(0, 40),
                        side: BorderSide(color: AppColors.primary.withValues(alpha: 0.3)),
                        foregroundColor: AppColors.primary,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            crossFadeState: _expanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            duration: const Duration(milliseconds: 250),
          ),
        ],
      ),
    );
  }
}

// -- 3-Segment Progress Bar --
class ThreeSegmentBar extends StatelessWidget {
  const ThreeSegmentBar({
    super.key,
    required this.green,
    required this.red,
    required this.gray,
  });
  final double green, red, gray;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: SizedBox(
        height: 8,
        child: Row(
          children: [
            if (green > 0)
              Expanded(
                flex: (green * 1000).round(),
                child: Container(color: AppColors.progressGreen),
              ),
            if (red > 0)
              Expanded(
                flex: (red * 1000).round(),
                child: Container(color: AppColors.progressRed),
              ),
            if (gray > 0)
              Expanded(
                flex: (gray * 1000).round(),
                child: Container(color: AppColors.progressGray),
              ),
          ],
        ),
      ),
    );
  }
}

// -- Topics List (expanded) --
class TopicsList extends StatelessWidget {
  const TopicsList({super.key, required this.topics});
  final List<GraphNode> topics;

  Color _dotColor(GraphNode n) {
    final pct = ((n.pMastery ?? 0) * 100).round();
    if (n.pMastery == null) return Colors.grey[300]!;
    if (pct >= 75) return AppColors.progressGreen;
    if (pct >= 60) return AppColors.progressOrange;
    return AppColors.progressRed;
  }

  @override
  Widget build(BuildContext context) {
    // Sort topics: tested first by mastery desc, untested at bottom
    final sorted = List<GraphNode>.from(topics)
      ..sort((a, b) {
        if (a.pMastery == null && b.pMastery != null) return 1;
        if (a.pMastery != null && b.pMastery == null) return -1;
        return (b.pMastery ?? 0).compareTo(a.pMastery ?? 0);
      });

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Column(
        children: [
          const Divider(height: 1),
          ...sorted.map((t) {
            final pct = t.pMastery != null
                ? ((t.pMastery! * 100).round())
                : null;
            final color = _dotColor(t);

            return InkWell(
              onTap: () => Navigator.of(context).pushNamed(
                PracticePage.routeName,
                arguments: {'nodeId': t.id, 'tagName': t.nameRu},
              ).then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  children: [
                    Container(
                      width: 10, height: 10,
                      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(t.nameRu,
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                          Text(pct != null ? 'Нажми чтобы практиковать' : 'Начать изучение',
                              style: TextStyle(fontSize: 11, color: Colors.grey[400])),
                        ],
                      ),
                    ),
                    if (pct != null)
                      Text('$pct%',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: color)),
                    if (pct == null)
                      Text('—', style: TextStyle(fontSize: 16, color: Colors.grey[300])),
                    const SizedBox(width: 4),
                    Icon(Icons.chevron_right, size: 18, color: Colors.grey[300]),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
