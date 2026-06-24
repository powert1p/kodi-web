import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import 'package:kodi_core/kodi_core.dart';
import '../bloc/dashboard_bloc.dart';
import '../../../app/colors.dart';
import '../../../app/error_l10n.dart';

class GraphPage extends StatelessWidget {
  const GraphPage({super.key});
  static const routeName = '/graph';

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    return BlocBuilder<DashboardBloc, DashboardState>(
      builder: (context, state) => Scaffold(
        backgroundColor: AppColors.surfaceAlt,
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          title: Text(l.graphTitle, style: const TextStyle(fontWeight: FontWeight.bold)),
          leading: const BackButton(),
        ),
        body: switch (state) {
          DashboardLoaded(
            :final nodes,
            :final topics,
            :final strands,
            :final student,
          ) => _GraphBody(
              nodes: nodes,
              topics: topics,
              strands: strands,
              lang: student.lang,
            ),
          DashboardError(:final message) => Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.error_outline, size: 48, color: AppColors.error),
              const SizedBox(height: 12),
              Text(localizeError(context, message), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => context.read<DashboardBloc>().add(DashboardLoad()),
                child: Text(l.retryBtn),
              ),
            ]),
          ),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
    );
  }
}

// ── Тело страницы с 3-уровневой иерархией ─────────────────────
class _GraphBody extends StatelessWidget {
  const _GraphBody({
    required this.nodes,
    required this.topics,
    required this.strands,
    required this.lang,
  });

  final List<GraphNode> nodes;
  final List<GraphTopic> topics;
  final List<GraphStrand> strands;
  final String lang;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;

    // Индексы для быстрого доступа
    final nodeById = <String, GraphNode>{for (final n in nodes) n.id: n};
    final topicById = <String, GraphTopic>{for (final t in topics) t.id: t};

    // Счётчики для легенды (по всем узлам)
    final mastered = nodes.where((n) => n.status == 'mastered').length;
    final partial  = nodes.where((n) => n.status == 'partial').length;
    final failed   = nodes.where((n) => n.status == 'failed').length;
    final untested = nodes.where((n) => n.status == 'untested').length;

    // Узлы, которые не попали ни в одну тему → раздел «Прочее»
    final coveredNodeIds = <String>{};
    for (final t in topics) {
      coveredNodeIds.addAll(t.nodeIds);
    }
    final orphanNodes = nodes.where((n) => !coveredNodeIds.contains(n.id)).toList();

    // Разделы, отсортированные по order
    final sortedStrands = [...strands]..sort((a, b) => a.order.compareTo(b.order));

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // ── Легенда ──
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))],
              ),
              child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                _LegendItem(color: AppColors.success, label: l.legendMastered, count: mastered),
                _LegendItem(color: AppColors.warning, label: l.legendPartial,  count: partial),
                _LegendItem(color: AppColors.error,   label: l.legendFailed,   count: failed),
                _LegendItem(color: AppColors.muted,   label: l.legendUntested, count: untested),
              ]),
            ),
            const SizedBox(height: 20),

            // ── Разделы → Темы → Навыки ──
            if (sortedStrands.isNotEmpty)
              ...sortedStrands.map((strand) {
                final strandTopics = topics
                    .where((t) => t.strand == strand.code)
                    .toList()
                  ..sort((a, b) => a.order.compareTo(b.order));

                // Агрегируем прогресс раздела по всем узлам его тем
                final allStrandNodeIds = strandTopics.expand((t) => t.nodeIds).toSet();
                final strandNodes = allStrandNodeIds
                    .map((id) => nodeById[id])
                    .whereType<GraphNode>()
                    .toList();

                return _StrandSection(
                  strand: strand,
                  strandTopics: strandTopics,
                  strandNodes: strandNodes,
                  nodeById: nodeById,
                  topicById: topicById,
                  lang: lang,
                );
              }),

            // ── Защитный раздел «Прочее» ──
            if (orphanNodes.isNotEmpty)
              _OrphanSection(nodes: orphanNodes, lang: lang, label: l.graphOther),
          ]),
        ),
      ),
    );
  }
}

// ── Раздел (strand) ────────────────────────────────────────────
class _StrandSection extends StatefulWidget {
  const _StrandSection({
    required this.strand,
    required this.strandTopics,
    required this.strandNodes,
    required this.nodeById,
    required this.topicById,
    required this.lang,
  });

  final GraphStrand strand;
  final List<GraphTopic> strandTopics;
  final List<GraphNode> strandNodes;
  final Map<String, GraphNode> nodeById;
  final Map<String, GraphTopic> topicById;
  final String lang;

  @override
  State<_StrandSection> createState() => _StrandSectionState();
}

class _StrandSectionState extends State<_StrandSection> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final mastered = widget.strandNodes.where((n) => n.status == 'mastered').length;
    final total    = widget.strandNodes.length;
    final pct      = total == 0 ? 0.0 : mastered / total;

    // Цвет прогресса и акцентная полоса — сигнал состояния раздела
    final accentColor = pct >= 0.75
        ? AppColors.progressGreen
        : pct >= 0.4
            ? AppColors.warning
            : pct > 0.0
                ? AppColors.error
                : AppColors.muted;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.04),
          blurRadius: 6,
          offset: const Offset(0, 2),
        )],
      ),
      // Подпись доступности: раздел — семантическая группа
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: IntrinsicWidth(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Шапка раздела с акцентной полосой ──
              InkWell(
                onTap: () => setState(() => _expanded = !_expanded),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        // Сигнатурный элемент: вертикальная полоса-акцент слева
                        Container(
                          width: 3,
                          height: 22,
                          margin: const EdgeInsets.only(right: 10),
                          decoration: BoxDecoration(
                            color: accentColor,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            widget.strand.name(widget.lang),
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        Text(
                          '$mastered/$total',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: pct >= 0.75 ? AppColors.progressGreen : AppColors.textSecondary,
                          ),
                        ),
                        const SizedBox(width: 8),
                        AnimatedRotation(
                          turns: _expanded ? 0.0 : -0.25,
                          duration: const Duration(milliseconds: 200),
                          child: const Icon(Icons.expand_more_rounded, size: 20, color: AppColors.textSecondary),
                        ),
                      ]),
                      const SizedBox(height: 8),
                      // Strand-level progress bar — толщина 8px, signature элемент
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: pct,
                          minHeight: 8,
                          backgroundColor: AppColors.border,
                          valueColor: AlwaysStoppedAnimation<Color>(accentColor),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // ── Список тем (раскрывающийся) ──
              AnimatedCrossFade(
                duration: const Duration(milliseconds: 250),
                crossFadeState: _expanded ? CrossFadeState.showFirst : CrossFadeState.showSecond,
                firstChild: widget.strandTopics.isNotEmpty
                    ? Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                        child: Column(
                          children: widget.strandTopics.map((topic) => _TopicSubCard(
                            topic: topic,
                            nodeById: widget.nodeById,
                            topicById: widget.topicById,
                            lang: widget.lang,
                          )).toList(),
                        ),
                      )
                    : const SizedBox.shrink(),
                secondChild: const SizedBox.shrink(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Под-карточка темы (topic) ──────────────────────────────────
class _TopicSubCard extends StatefulWidget {
  const _TopicSubCard({
    required this.topic,
    required this.nodeById,
    required this.topicById,
    required this.lang,
  });

  final GraphTopic topic;
  final Map<String, GraphNode> nodeById;
  final Map<String, GraphTopic> topicById;
  final String lang;

  @override
  State<_TopicSubCard> createState() => _TopicSubCardState();
}

class _TopicSubCardState extends State<_TopicSubCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;

    // Узлы темы, которые реально есть в данных
    final topicNodes = widget.topic.nodeIds
        .map((id) => widget.nodeById[id])
        .whereType<GraphNode>()
        .toList();

    final mastered = topicNodes.where((n) => n.status == 'mastered').length;
    final total    = topicNodes.length;
    final pct      = total == 0 ? 0.0 : mastered / total;

    final barColor = pct >= 0.75
        ? AppColors.progressGreen
        : pct >= 0.4
            ? AppColors.warning
            : pct > 0.0
                ? AppColors.error
                : AppColors.muted;

    // Резолвим prereq → имена тем (пропускаем нерезолвящиеся)
    final prereqNames = widget.topic.prereq
        .map((id) => widget.topicById[id]?.name(widget.lang))
        .whereType<String>()
        .toList();

    return Container(
      margin: const EdgeInsets.only(top: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border, width: 1),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Заголовок темы
        InkWell(
          onTap: topicNodes.isNotEmpty
              ? () => setState(() => _expanded = !_expanded)
              : null,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                  child: Text(
                    widget.topic.name(widget.lang),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                Text(
                  '$mastered/$total',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: pct >= 0.75 ? AppColors.progressGreen : AppColors.textSecondary,
                  ),
                ),
                if (topicNodes.isNotEmpty) ...[
                  const SizedBox(width: 6),
                  AnimatedRotation(
                    turns: _expanded ? 0.0 : -0.25,
                    duration: const Duration(milliseconds: 200),
                    child: const Icon(Icons.expand_more_rounded, size: 16, color: AppColors.muted),
                  ),
                ],
              ]),
              const SizedBox(height: 6),
              // Тонкий progress bar темы (4px)
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(
                  value: pct,
                  minHeight: 4,
                  backgroundColor: AppColors.border,
                  valueColor: AlwaysStoppedAnimation<Color>(barColor),
                ),
              ),
              // Строка «Опирается на:» — только если есть prereq
              if (prereqNames.isNotEmpty) ...[
                const SizedBox(height: 5),
                Text(
                  '${l.graphReliesOn}: ${prereqNames.join(', ')}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.muted,
                    height: 1.4,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ]),
          ),
        ),
        // Список навыков (раскрывающийся)
        AnimatedCrossFade(
          duration: const Duration(milliseconds: 200),
          crossFadeState: _expanded ? CrossFadeState.showFirst : CrossFadeState.showSecond,
          firstChild: topicNodes.isNotEmpty
              ? Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                  child: Column(
                    children: topicNodes.map((n) => _NodeRow(node: n, lang: widget.lang)).toList(),
                  ),
                )
              : const SizedBox.shrink(),
          secondChild: const SizedBox.shrink(),
        ),
      ]),
    );
  }
}

// ── Защитный раздел «Прочее» ───────────────────────────────────
class _OrphanSection extends StatelessWidget {
  const _OrphanSection({
    required this.nodes,
    required this.lang,
    required this.label,
  });

  final List<GraphNode> nodes;
  final String lang;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.04),
          blurRadius: 6,
          offset: const Offset(0, 2),
        )],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.bold,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          ...nodes.map((n) => _NodeRow(node: n, lang: lang)),
        ]),
      ),
    );
  }
}

// ── Легенда (без изменений) ────────────────────────────────────
class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label, required this.count});
  final Color color;
  final String label;
  final int count;

  @override
  Widget build(BuildContext context) => Column(children: [
    Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
    const SizedBox(height: 4),
    Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
    Text('$count', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
  ]);
}

// ── Строка навыка (без изменений) ─────────────────────────────
class _NodeRow extends StatelessWidget {
  const _NodeRow({required this.node, required this.lang});
  final GraphNode node;
  final String lang;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (node.status) {
      'mastered' => (AppColors.success,     Icons.check_circle_rounded),
      'partial'  => (AppColors.warning,     Icons.radio_button_checked_rounded),
      'failed'   => (AppColors.error,       Icons.cancel_rounded),
      _          => (AppColors.borderLight, Icons.radio_button_unchecked_rounded),
    };
    final pct = node.pMastery != null
        ? '${(node.pMastery! * 100).toStringAsFixed(0)}%'
        : '—';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Icon(icon, color: color, size: 16),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            node.name(lang),
            style: const TextStyle(fontSize: 13, color: AppColors.textPrimary),
          ),
        ),
        Text(pct, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w500)),
        if (node.isFringe) ...[
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: AppColors.primaryBgLight,
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Text('◎', style: TextStyle(fontSize: 10, color: AppColors.primary)),
          ),
        ],
      ]),
    );
  }
}
