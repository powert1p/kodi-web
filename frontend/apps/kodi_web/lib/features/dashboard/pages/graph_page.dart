import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../bloc/dashboard_bloc.dart';

class GraphPage extends StatelessWidget {
  const GraphPage({super.key});
  static const routeName = '/graph';

  static const _tagLabels = {
    'arithmetic': 'Арифметика', 'fractions': 'Дроби', 'algebra': 'Алгебра',
    'geometry': 'Геометрия', 'word_problems': 'Текстовые задачи',
    'number_theory': 'Теория чисел', 'combinatorics': 'Комбинаторика',
    'probability': 'Вероятность', 'statistics': 'Статистика',
    'equations': 'Уравнения', 'decimals': 'Десятичные дроби',
    'ratios': 'Пропорции и проценты', 'modulus': 'Модуль числа',
    'sequences': 'Последовательности', 'sets': 'Множества',
    'negative': 'Отрицательные числа', 'rounding': 'Округление',
    'measurement': 'Единицы измерения', 'data_analysis': 'Анализ данных',
    'divisibility': 'Делимость', 'logic': 'Логика',
  };

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<DashboardBloc, DashboardState>(
      builder: (context, state) => Scaffold(
        backgroundColor: const Color(0xFFF1F5F9),
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          title: const Text('Граф знаний', style: TextStyle(fontWeight: FontWeight.bold)),
          leading: const BackButton(),
        ),
        body: switch (state) {
          DashboardLoaded(:final nodes, :final student) => _GraphBody(nodes: nodes, lang: student.lang),
          DashboardError(:final message) => Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.error_outline, size: 48, color: Color(0xFFEF4444)),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => context.read<DashboardBloc>().add(DashboardLoad()),
                child: const Text('Повторить'),
              ),
            ]),
          ),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
    );
  }
}

class _GraphBody extends StatelessWidget {
  const _GraphBody({required this.nodes, required this.lang});
  final List<GraphNode> nodes; final String lang;

  @override
  Widget build(BuildContext context) {
    final byTag = <String, List<GraphNode>>{};
    for (final n in nodes) { byTag.putIfAbsent(n.tag, () => []).add(n); }

    final mastered = nodes.where((n) => n.status == 'mastered').length;
    final partial = nodes.where((n) => n.status == 'partial').length;
    final failed = nodes.where((n) => n.status == 'failed').length;
    final untested = nodes.where((n) => n.status == 'untested').length;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // Legend
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
              child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                _LegendItem(color: const Color(0xFF10B981), label: 'Освоено', count: mastered),
                _LegendItem(color: const Color(0xFFF59E0B), label: 'Частично', count: partial),
                _LegendItem(color: const Color(0xFFEF4444), label: 'Провалено', count: failed),
                _LegendItem(color: const Color(0xFF94A3B8), label: 'Не проверено', count: untested),
              ]),
            ),
            const SizedBox(height: 20),
            ...byTag.entries.map((e) => _CategorySection(
              tag: e.key,
              label: GraphPage._tagLabels[e.key] ?? e.key,
              nodes: e.value,
              lang: lang,
            )),
          ]),
        ),
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label, required this.count});
  final Color color; final String label; final int count;
  @override
  Widget build(BuildContext context) => Column(children: [
    Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
    const SizedBox(height: 4),
    Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
    Text('$count', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
  ]);
}

class _CategorySection extends StatelessWidget {
  const _CategorySection({required this.tag, required this.label, required this.nodes, required this.lang});
  final String tag, label; final List<GraphNode> nodes; final String lang;

  @override
  Widget build(BuildContext context) {
    final mastered = nodes.where((n) => n.status == 'mastered').length;
    final pct = nodes.isEmpty ? 0.0 : mastered / nodes.length;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))]),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)))),
            Text('$mastered/${nodes.length}',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600,
                color: pct > 0.7 ? const Color(0xFF10B981) : const Color(0xFF64748B))),
          ]),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: pct, minHeight: 8,
              backgroundColor: const Color(0xFFE2E8F0),
              valueColor: AlwaysStoppedAnimation<Color>(pct > 0.7 ? const Color(0xFF10B981) : pct > 0.3 ? const Color(0xFFF59E0B) : const Color(0xFF2563EB)),
            ),
          ),
          const SizedBox(height: 12),
          ...nodes.map((n) => _NodeRow(node: n, lang: lang)),
        ]),
      ),
    );
  }
}

class _NodeRow extends StatelessWidget {
  const _NodeRow({required this.node, required this.lang});
  final GraphNode node; final String lang;
  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (node.status) {
      'mastered' => (const Color(0xFF10B981), Icons.check_circle_rounded),
      'partial'  => (const Color(0xFFF59E0B), Icons.radio_button_checked_rounded),
      'failed'   => (const Color(0xFFEF4444), Icons.cancel_rounded),
      _          => (const Color(0xFFCBD5E1), Icons.radio_button_unchecked_rounded),
    };
    final pct = node.pMastery != null ? '${(node.pMastery! * 100).toStringAsFixed(0)}%' : '—';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Icon(icon, color: color, size: 16),
        const SizedBox(width: 8),
        Expanded(child: Text(node.name(lang), style: const TextStyle(fontSize: 13, color: Color(0xFF1E293B)))),
        Text(pct, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w500)),
        if (node.isFringe) ...[
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: const Color(0xFFEFF6FF), borderRadius: BorderRadius.circular(4)),
            child: const Text('◎', style: TextStyle(fontSize: 10, color: Color(0xFF2563EB))),
          ),
        ],
      ]),
    );
  }
}
