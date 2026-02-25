import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../../app/colors.dart';
import '../../bloc/dashboard_bloc.dart';
import '../../../practice/pages/practice_page.dart';
import 'section_data.dart';

class ProblemSectionCard extends StatefulWidget {
  const ProblemSectionCard({super.key, required this.section});
  final SectionData section;
  @override
  State<ProblemSectionCard> createState() => _ProblemSectionCardState();
}

class _ProblemSectionCardState extends State<ProblemSectionCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    final s = widget.section;
    final incorrect = s.problemsSolved - s.problemsCorrect;
    final accuracy = s.problemsSolved > 0
        ? (s.problemsCorrect / s.problemsSolved * 100).round()
        : 0;

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
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Text(s.icon, style: const TextStyle(fontSize: 28)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(s.nameRu,
                            style: const TextStyle(
                                fontWeight: FontWeight.w600, fontSize: 16)),
                        const SizedBox(height: 2),
                        Text(
                          s.problemsSolved > 0
                              ? '✅ ${ s.problemsCorrect}  ❌ $incorrect'
                              : l.noSolvedProblems,
                          style: TextStyle(fontSize: 12, color: Colors.grey[500]),
                        ),
                      ],
                    ),
                  ),
                  if (s.problemsSolved > 0) ...[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('${s.problemsSolved}',
                            style: const TextStyle(
                                fontSize: 20, fontWeight: FontWeight.bold,
                                color: AppColors.primary)),
                        Text('$accuracy%',
                            style: TextStyle(fontSize: 12, color: Colors.grey[500])),
                      ],
                    ),
                    const SizedBox(width: 8),
                  ],
                  AnimatedRotation(
                    turns: _expanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 200),
                    child: Icon(Icons.keyboard_arrow_down,
                        color: Colors.grey[400]),
                  ),
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            firstChild: const SizedBox.shrink(),
            secondChild: ProblemTopicsList(topics: s.topics),
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

// -- Problem Topics List (expanded, by tasks) --
class ProblemTopicsList extends StatelessWidget {
  const ProblemTopicsList({super.key, required this.topics});
  final List<GraphNode> topics;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    final lang = context.read<NisApiClient>().lang;
    final sorted = List<GraphNode>.from(topics)
      ..sort((a, b) => b.qTotal.compareTo(a.qTotal));

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Column(
        children: [
          const Divider(height: 1),
          ...sorted.map((t) {
            final accuracy = t.qTotal > 0
                ? (t.qCorrect / t.qTotal * 100).round()
                : 0;
            final incorrect = t.qTotal - t.qCorrect;

            return InkWell(
              onTap: () => Navigator.of(context).pushNamed(
                PracticePage.routeName,
                arguments: {'nodeId': t.id, 'tagName': t.name(lang)},
              ).then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(t.name(lang),
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                          if (t.qTotal > 0)
                            Text('✅ ${t.qCorrect}  ❌ $incorrect  ·  $accuracy%',
                                style: TextStyle(fontSize: 11, color: Colors.grey[400]))
                          else
                            Text(l.notSolvedYet,
                                style: TextStyle(fontSize: 11, color: Colors.grey[400])),
                        ],
                      ),
                    ),
                    Text(t.qTotal > 0 ? '${t.qTotal}' : '—',
                        style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: t.qTotal > 0 ? AppColors.primary : Colors.grey[300])),
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
