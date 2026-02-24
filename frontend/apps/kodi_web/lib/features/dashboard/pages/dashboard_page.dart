import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import 'package:kodi_core/kodi_core.dart';
import '../bloc/dashboard_bloc.dart';
import '../../auth/bloc/auth_bloc.dart';
import '../../../app/locale_bloc.dart';
import '../../practice/pages/practice_page.dart';
import '../../../shared/utils/responsive.dart';
import 'graph_page.dart';
import 'leaderboard_page.dart';
import '../../diagnostic/pages/diagnostic_page.dart';
import '../../../shared/constants/tag_labels.dart';
import '../../../app/colors.dart';
import 'widgets/section_data.dart';
import 'widgets/error_view.dart';
import 'widgets/hero_card.dart';
import 'widgets/stats_row.dart';
import 'widgets/section_card.dart';
import 'widgets/problem_section_card.dart';
import 'widgets/onboarding_view.dart';
import 'widgets/resume_banner.dart';
import 'widgets/tab_chip.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});
  static const routeName = '/';
  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  @override
  void initState() {
    super.initState();
    context.read<DashboardBloc>().add(DashboardLoad());
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    return BlocBuilder<DashboardBloc, DashboardState>(
      builder: (context, state) => Scaffold(
        backgroundColor: AppColors.scaffoldBg,
        appBar: AppBar(
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.white,
          elevation: 0.5,
          title: Row(children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.school_rounded,
                  color: Colors.white, size: 20),
            ),
            const SizedBox(width: 10),
            const Text('NIS Math',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          ]),
          actions: [
            if (state is DashboardLoaded)
              Padding(
                padding: const EdgeInsets.only(right: 4),
                child: TextButton.icon(
                  onPressed: () =>
                      Navigator.of(context).pushNamed(GraphPage.routeName).then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                  icon: const Icon(Icons.hub_rounded, size: 18),
                  label: Text(l.graphBtn),
                ),
              ),
            BlocBuilder<LocaleBloc, LocaleState>(
              builder: (context, localeState) {
                final isRu = localeState.locale.languageCode == 'ru';
                return TextButton(
                  onPressed: () {
                    final next = isRu ? const Locale('kk') : const Locale('ru');
                    context.read<LocaleBloc>().add(LocaleChanged(next));
                    context.read<DashboardBloc>().add(DashboardLoad());
                  },
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    minimumSize: const Size(0, 36),
                  ),
                  child: Text(
                    isRu ? 'ҚК' : 'РУ',
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                  ),
                );
              },
            ),
            IconButton(
              icon: const Icon(Icons.logout_rounded, size: 20),
              onPressed: () => context.read<AuthBloc>().add(AuthLogout()),
              tooltip: l.logoutTooltip,
            ),
            const SizedBox(width: 8),
          ],
        ),
        body: switch (state) {
          DashboardLoading() || DashboardInitial() =>
            const Center(child: CircularProgressIndicator()),
          DashboardError(:final message) => ErrorView(
              message: message,
              onRetry: () =>
                  context.read<DashboardBloc>().add(DashboardLoad())),
          DashboardLoaded(:final student, :final stats, :final nodes, :final leaderboard) =>
            _Body(student: student, stats: stats, nodes: nodes, leaderboard: leaderboard),
          _ => const SizedBox.shrink(),
        },
      ),
    );
  }
}

// -- Body --
class _Body extends StatefulWidget {
  const _Body(
      {super.key, required this.student, required this.stats, required this.nodes, required this.leaderboard});
  final Student student;
  final Stats stats;
  final List<GraphNode> nodes;
  final List<LeaderboardEntry> leaderboard;

  @override
  State<_Body> createState() => _BodyState();
}

class _BodyState extends State<_Body> {
  int _tabIndex = 0; // 0 = By topics, 1 = By problems

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    final student = widget.student;
    final stats = widget.stats;
    final nodes = widget.nodes;
    final leaderboard = widget.leaderboard;
    // Check if new student (no mastery data)
    final hasAnyMastery = nodes.any((n) => n.pMastery != null);

    if (!hasAnyMastery) {
      return OnboardingView(student: student);
    }

    // Group nodes by tag -> build sections
    final byTag = <String, List<GraphNode>>{};
    for (final n in nodes) {
      byTag.putIfAbsent(n.tag, () => []).add(n);
    }

    final sections = byTag.entries.map((e) {
      final tag = e.key;
      final topics = e.value;
      final tested = topics.where((t) => t.pMastery != null).toList();
      final testedCount = tested.length;
      final totalCount = topics.length;
      final avgPct = testedCount > 0
          ? (tested.fold<double>(0, (s, t) => s + (t.pMastery ?? 0)) /
                  testedCount *
                  100)
              .round()
          : 0;
      final mastered =
          topics.where((t) => (t.pMastery ?? 0) >= 0.85).length;
      final failed = topics
          .where((t) => t.pMastery != null && t.pMastery! < 0.85)
          .length;
      final untested = totalCount - testedCount;

      final pSolved = topics.fold<int>(0, (s, t) => s + t.qTotal);
      final pCorrect = topics.fold<int>(0, (s, t) => s + t.qCorrect);

      return SectionData(
        tag: tag,
        nameRu: TagLabels.label(tag, compact: true),
        icon: _sectionIcons[tag] ?? '📘',
        testedCount: testedCount,
        totalCount: totalCount,
        percentage: avgPct,
        barGreen: totalCount > 0 ? mastered / totalCount : 0,
        barRed: totalCount > 0 ? failed / totalCount : 0,
        barGray: totalCount > 0 ? untested / totalCount : 0,
        topics: topics,
        problemsSolved: pSolved,
        problemsCorrect: pCorrect,
      );
    }).toList();

    // Sort: tested sections first by % desc, untested at bottom
    sections.sort((a, b) {
      if (a.testedCount == 0 && b.testedCount > 0) return 1;
      if (a.testedCount > 0 && b.testedCount == 0) return -1;
      return b.percentage.compareTo(a.percentage);
    });

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: EdgeInsets.all(rp(context, 16)),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                HeroCard(student: student, stats: stats),
                if (student.hasPausedDiagnostic) ...[
                  const SizedBox(height: 12),
                  ResumeBanner(onResume: () {
                    Navigator.of(context)
                        .pushNamed(DiagnosticPage.routeName)
                        .then((_) => context.read<DashboardBloc>().add(DashboardLoad()));
                  }),
                ],
                const SizedBox(height: 16),
                StatsRow(stats: stats),
                const SizedBox(height: 16),
                LayoutBuilder(builder: (context, constraints) {
                  final small = constraints.maxWidth < 360;
                  final btnFontSize = rs(context, small ? 12 : 14);
                  final iconSize = rs(context, small ? 18 : 20);
                  final btnHeight = rs(context, 48);
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      SizedBox(
                        width: small ? constraints.maxWidth : (constraints.maxWidth - 16) / 3,
                        child: FilledButton.icon(
                          onPressed: () => Navigator.of(context)
                              .pushNamed(DiagnosticPage.routeName)
                              .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                          icon: Icon(Icons.psychology_rounded, size: iconSize),
                          label: Text(l.dashboardDiagnostic,
                              style: TextStyle(fontSize: btnFontSize, fontWeight: FontWeight.w600)),
                          style: FilledButton.styleFrom(
                              minimumSize: Size(0, btnHeight),
                              backgroundColor: AppColors.purple),
                        ),
                      ),
                      SizedBox(
                        width: small ? constraints.maxWidth : (constraints.maxWidth - 16) / 3,
                        child: FilledButton.icon(
                          onPressed: () => Navigator.of(context)
                              .pushNamed(PracticePage.routeName)
                              .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                          icon: Icon(Icons.play_arrow_rounded, size: iconSize),
                          label: Text(l.dashboardPractice,
                              style: TextStyle(fontSize: btnFontSize, fontWeight: FontWeight.w600)),
                          style: FilledButton.styleFrom(
                              minimumSize: Size(0, btnHeight),
                              backgroundColor: AppColors.primary),
                        ),
                      ),
                      SizedBox(
                        width: small ? constraints.maxWidth : (constraints.maxWidth - 16) / 3,
                        child: FilledButton.icon(
                          onPressed: () => Navigator.of(context)
                              .pushNamed(LeaderboardPage.routeName,
                                  arguments: leaderboard)
                              .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                          icon: Icon(Icons.emoji_events_rounded, size: iconSize),
                          label: Text(l.dashboardLeaderboard,
                              style: TextStyle(fontSize: btnFontSize, fontWeight: FontWeight.w600)),
                          style: FilledButton.styleFrom(
                              minimumSize: Size(0, btnHeight),
                              backgroundColor: AppColors.comboEnd),
                        ),
                      ),
                    ],
                  );
                }),
                const SizedBox(height: 24),
                // -- Tab switcher --
                Row(
                  children: [
                    Text(l.sectionsHeader,
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey[500],
                            letterSpacing: 1.2)),
                    const Spacer(),
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.grey[200],
                        borderRadius: BorderRadius.circular(8),
                      ),
                      padding: const EdgeInsets.all(2),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TabChip(
                            label: l.tabTopics,
                            selected: _tabIndex == 0,
                            onTap: () => setState(() => _tabIndex = 0),
                          ),
                          TabChip(
                            label: l.tabProblems,
                            selected: _tabIndex == 1,
                            onTap: () => setState(() => _tabIndex = 1),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (_tabIndex == 0)
                  ...sections.map((s) => SectionCard(section: s))
                else
                  ...sections.map((s) => ProblemSectionCard(section: s)),
              ]),
        ),
      ),
    );
  }

  static const _sectionIcons = {
    'arithmetic': '🔢',
    'fractions': '🍕',
    'decimals': '🔟',
    'divisibility': '➗',
    'equations': '⚖️',
    'geometry': '📐',
    'algebra': '🔤',
    'word_problems': '📝',
    'proportion': '🏗️',
    'percent': '📊',
    'numbers': '🔢',
    'conversion': '📏',
    'logic': '🧩',
    'sets': '🔵',
    'data': '📈',
  };
}
