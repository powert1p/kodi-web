import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../shared/widgets/problem_card.dart';
import '../../../shared/widgets/answer_input.dart';
import '../../../shared/widgets/result_card.dart';
import '../../../shared/widgets/report_sheet.dart';
import '../../../shared/utils/responsive.dart';
import '../../../app/colors.dart';
import '../bloc/diagnostic_bloc.dart';

class DiagnosticPage extends StatefulWidget {
  const DiagnosticPage({super.key});
  static const routeName = '/diagnostic';
  @override
  State<DiagnosticPage> createState() => _DiagnosticPageState();
}

class _DiagnosticPageState extends State<DiagnosticPage> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _keyboardFocus = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    super.dispose();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    final state = context.read<DiagnosticBloc>().state;
    if (state is DiagnosticAnswerShown &&
        (event.logicalKey == LogicalKeyboardKey.arrowRight ||
         event.logicalKey == LogicalKeyboardKey.space)) {
      final hasNext = state.answerResult['has_next'] == true;
      if (hasNext) {
        context.read<DiagnosticBloc>().add(DiagnosticNextQuestionRequested());
      } else {
        context.read<DiagnosticBloc>().add(DiagnosticFinishRequested());
      }
    }
  }

  Future<bool> _onWillPop(DiagnosticState state) async {
    final isActive = state is DiagnosticQuestionReady ||
        state is DiagnosticAnswerShown ||
        state is DiagnosticLoading;
    if (!isActive) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Покинуть диагностику?'),
        content: const Text(
          'Прогресс будет сохранён — вы сможете продолжить позже.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Остаться')),
          TextButton(onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Выйти')),
        ],
      ),
    );
    return leave ?? false;
  }

  String _fmtTime(int s) => s < 60 ? '${s}с' : '${s ~/ 60}м ${s % 60}с';

  bool _isActiveSession(DiagnosticState state) =>
      state is DiagnosticQuestionReady ||
      state is DiagnosticAnswerShown;

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<DiagnosticBloc, DiagnosticState>(
      listener: (context, state) {
        if (state is DiagnosticQuestionReady) {
          _controller.clear();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _focusNode.requestFocus();
          });
        }
        if (state is DiagnosticError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.message)));
        }
      },
      builder: (context, state) {
        final canPop = !_isActiveSession(state) && state is! DiagnosticLoading;
        return PopScope(
          canPop: canPop,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final shouldLeave = await _onWillPop(state);
            if (shouldLeave && context.mounted) Navigator.of(context).pop();
          },
          child: KeyboardListener(
            focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
            child: Scaffold(
              backgroundColor: AppColors.scaffoldBg,
              appBar: _buildAppBar(context, state),
              body: state is DiagnosticLoading
                  ? const Center(child: CircularProgressIndicator())
                  : Align(alignment: Alignment.topCenter,
                      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.all(16),
                          child: _buildContent(context, state)))),
            )),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context, DiagnosticState state) {
    return AppBar(
      backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
      leading: BackButton(onPressed: () async {
        if (!_isActiveSession(state)) { Navigator.of(context).pop(); return; }
        final shouldLeave = await _onWillPop(state);
        if (shouldLeave && context.mounted) Navigator.of(context).pop();
      }),
      title: Row(children: [
        const Text('Диагностика',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        if (state is DiagnosticQuestionReady) ...[
          const Spacer(),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Text(_fmtTime(state.elapsedSeconds),
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
                color: state.elapsedSeconds > 120 ? AppColors.error : Colors.grey[400],
                fontFeatures: const [FontFeature.tabularFigures()]))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primaryBgLight,
              borderRadius: BorderRadius.circular(20)),
            child: Text('${state.topicsTested + 1}/${state.maxTopics}',
              style: const TextStyle(color: AppColors.primary,
                fontSize: 13, fontWeight: FontWeight.w600))),
        ],
        if (state is DiagnosticAnswerShown) ...[
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primaryBgLight,
              borderRadius: BorderRadius.circular(20)),
            child: Text('${state.topicsTested + 1}/${state.maxTopics}',
              style: const TextStyle(color: AppColors.primary,
                fontSize: 13, fontWeight: FontWeight.w600))),
        ],
      ]));
  }

  Widget _buildContent(BuildContext context, DiagnosticState state) {
    return switch (state) {
      DiagnosticError(:final message) => _buildError(context, message),
      DiagnosticFinished() => _buildResults(context, state),
      DiagnosticActiveSessionFound() => _buildResumePrompt(context, state),
      DiagnosticModeSelection() => _buildStart(context),
      DiagnosticQuestionReady() => _buildQuestion(context, state),
      DiagnosticAnswerShown() => _buildAnswerResult(context, state),
      _ => const SizedBox.shrink(),
    };
  }

  Widget _buildResumePrompt(BuildContext context, DiagnosticActiveSessionFound state) {
    final modeName = state.activeMode == 'gaps' ? 'Проверка пробелов' : 'Подготовка к экзамену';
    final bloc = context.read<DiagnosticBloc>();
    return Column(children: [
      const SizedBox(height: 40),
      Container(
        width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          color: AppColors.orange,
          borderRadius: BorderRadius.circular(20)),
        child: Icon(Icons.pause_circle_filled_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text('Незавершённая диагностика',
        style: TextStyle(fontSize: rs(context, 22), fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
      const SizedBox(height: 12),
      Text('$modeName — ${state.activeTopicsTested} из ${state.activeMaxTopics} тем · ${state.activeQuestionsAsked} вопросов',
        style: TextStyle(fontSize: 15, color: Colors.grey[600], height: 1.5),
        textAlign: TextAlign.center),
      const SizedBox(height: 8),
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: state.activeMaxTopics > 0 ? state.activeTopicsTested / state.activeMaxTopics : 0,
          minHeight: 8,
          backgroundColor: AppColors.border,
          valueColor: const AlwaysStoppedAnimation(AppColors.orange))),
      const SizedBox(height: 32),
      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () => bloc.add(DiagnosticResumeRequested()),
          icon: const Icon(Icons.play_arrow_rounded),
          label: const Text('Продолжить',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: FilledButton.styleFrom(
            minimumSize: const Size(0, 52),
            backgroundColor: AppColors.orange))),
      const SizedBox(height: 12),
      SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: () => bloc.add(DiagnosticDismissResumePrompt()),
          icon: const Icon(Icons.restart_alt_rounded),
          label: const Text('Начать заново',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 52)))),
    ]);
  }

  Widget _buildStart(BuildContext context) {
    final bloc = context.read<DiagnosticBloc>();
    return Column(children: [
      const SizedBox(height: 40),
      Container(
        width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [AppColors.gradientPurpleStart, AppColors.gradientPurpleEnd]),
          borderRadius: BorderRadius.circular(20)),
        child: Icon(Icons.psychology_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text('Диагностика знаний',
        style: TextStyle(fontSize: rs(context, 24), fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
      const SizedBox(height: 12),
      Text('15 тем — адаптивный алгоритм подберёт задачи под тебя.',
        style: TextStyle(fontSize: 15, color: Colors.grey[600], height: 1.5),
        textAlign: TextAlign.center),
      const SizedBox(height: 32),
      _ModeCard(
        title: 'Готовлюсь к экзамену', subtitle: '15 тем · 10-15 минут',
        description: 'Сложные темы первыми — проверь готовность',
        icon: Icons.school_rounded, color: AppColors.primary,
        onStart: () => bloc.add(DiagnosticCancelAndStartNew('exam'))),
      const SizedBox(height: 12),
      _ModeCard(
        title: 'Проверяю пробелы', subtitle: '15 тем · 10-15 минут',
        description: 'С базовых тем вверх — найди слабые места',
        icon: Icons.search_rounded, color: AppColors.purple,
        onStart: () => bloc.add(DiagnosticCancelAndStartNew('gaps'))),
    ]);
  }

  Widget _buildQuestion(BuildContext context, DiagnosticQuestionReady state) {
    final q = state.question;
    final text = q['text'] as String? ?? '';
    final nodeName = q['node_name'] as String?;
    final bloc = context.read<DiagnosticBloc>();
    final api = context.read<NisApiClient>();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: state.maxTopics > 0 ? state.topicsTested / state.maxTopics : 0,
          minHeight: 6,
          backgroundColor: AppColors.border,
          valueColor: const AlwaysStoppedAnimation(AppColors.primary))),
      const SizedBox(height: 4),
      Row(children: [
        Text('Тема ${state.topicsTested + 1} из ${state.maxTopics}',
          style: TextStyle(fontSize: 12, color: Colors.grey[500])),
        const Spacer(),
        Text('${state.correctCount} правильно',
          style: const TextStyle(fontSize: 12, color: AppColors.success, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 16),

      ProblemCard(
        text: text,
        nodeName: nodeName,
        counter: '${state.questionsAsked + 1}'),
      const SizedBox(height: 16),

      AnswerInput(
        controller: _controller,
        focusNode: _focusNode,
        onSubmit: () => bloc.add(DiagnosticAnswerSubmitted(_controller.text.trim())),
        onReport: () => showReportSheet(context, api, q['problem_id']),
      ),
    ]);
  }

  Widget _buildAnswerResult(BuildContext context, DiagnosticAnswerShown state) {
    final r = state.answerResult;
    final ok = r['is_correct'] == true;
    final hasNext = r['has_next'] == true;
    final bloc = context.read<DiagnosticBloc>();
    final api = context.read<NisApiClient>();

    return Column(children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: state.maxTopics > 0 ? state.topicsTested / state.maxTopics : 0,
          minHeight: 6,
          backgroundColor: AppColors.border,
          valueColor: const AlwaysStoppedAnimation(AppColors.primary))),
      const SizedBox(height: 16),

      ResultCard(
        isCorrect: ok,
        correctAnswer: r['correct_answer']?.toString(),
        solution: r['solution'] as String?,
        nodeName: state.question['node_name'] as String?,
        onReport: !ok ? () => showReportSheet(context, api, state.question['problem_id']) : null,
      ),
      const SizedBox(height: 16),

      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: hasNext
              ? () => bloc.add(DiagnosticNextQuestionRequested())
              : () => bloc.add(DiagnosticFinishRequested()),
          icon: Icon(hasNext ? Icons.arrow_forward_rounded : Icons.flag_rounded),
          label: Row(mainAxisSize: MainAxisSize.min, children: [
            Text(hasNext ? 'Следующая' : 'Завершить',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            if (hasNext) ...[
              const SizedBox(width: 8),
              const Text('→', style: TextStyle(fontSize: 14, color: Colors.white70)),
            ],
          ]),
          style: FilledButton.styleFrom(
            minimumSize: const Size(0, 52),
            backgroundColor: AppColors.primary))),
      if (hasNext) ...[
        const SizedBox(height: 8),
        Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
      ],
    ]);
  }

  Widget _buildResults(BuildContext context, DiagnosticFinished state) {
    final r = state.results;
    final mastered = (r['mastered_nodes'] as List?)?.length ?? 0;
    final failed = (r['failed_nodes'] as List?)?.length ?? 0;
    final summary = r['summary'] as String? ?? '';
    final masteredNodes = (r['mastered_nodes'] as List?) ?? [];
    final failedNodes = (r['failed_nodes'] as List?) ?? [];

    return Column(children: [
      const SizedBox(height: 20),
      Container(
        width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          color: AppColors.success,
          borderRadius: BorderRadius.circular(20)),
        child: Icon(Icons.check_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text('Диагностика завершена!',
        style: TextStyle(fontSize: rs(context, 22), fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
      const SizedBox(height: 8),
      Text(summary, style: TextStyle(fontSize: rs(context, 14), color: Colors.grey[600]),
        textAlign: TextAlign.center),
      const SizedBox(height: 24),

      Row(children: [
        Expanded(child: _ResultStat(label: 'Освоено', value: '$mastered', color: AppColors.success)),
        const SizedBox(width: 10),
        Expanded(child: _ResultStat(label: 'Пробелы', value: '$failed', color: AppColors.error)),
        const SizedBox(width: 10),
        Expanded(child: _ResultStat(label: 'Правильно', value: '${state.correctCount}', color: AppColors.primary)),
      ]),
      const SizedBox(height: 20),

      if (masteredNodes.isNotEmpty)
        _TopicList(title: '✅ Освоенные темы', topics: masteredNodes, color: AppColors.success),
      if (failedNodes.isNotEmpty)
        _TopicList(title: '❌ Слабые темы', topics: failedNodes, color: AppColors.error),

      const SizedBox(height: 24),
      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.home_rounded),
          label: const Text('На главную',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: FilledButton.styleFrom(
            minimumSize: const Size(0, 52),
            backgroundColor: AppColors.primary))),
    ]);
  }

  Widget _buildError(BuildContext context, String message) {
    return Column(children: [
      const SizedBox(height: 40),
      Icon(Icons.error_outline, size: 48, color: Colors.red[300]),
      const SizedBox(height: 16),
      Text('Что-то пошло не так', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.grey[700])),
      const SizedBox(height: 8),
      Text(message, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey[500], fontSize: 13)),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: () => context.read<DiagnosticBloc>().add(DiagnosticErrorDismissed()),
        child: const Text('Попробовать снова')),
    ]);
  }
}

class _ModeCard extends StatelessWidget {
  const _ModeCard({required this.title, required this.subtitle,
    required this.description, required this.icon, required this.color, required this.onStart});
  final String title, subtitle, description;
  final IconData icon;
  final Color color;
  final VoidCallback onStart;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity, padding: EdgeInsets.all(rp(context, 20)),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))]),
      child: Row(children: [
        Container(width: rs(context, 48), height: rs(context, 48),
          decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
          child: Icon(icon, color: color, size: rs(context, 26))),
        SizedBox(width: rp(context, 16)),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.w600, fontSize: rs(context, 15))),
          Text(subtitle, style: TextStyle(fontSize: rs(context, 12), color: Colors.grey[500])),
          const SizedBox(height: 2),
          Text(description, style: TextStyle(fontSize: rs(context, 12), color: Colors.grey[400])),
        ])),
        FilledButton(onPressed: onStart,
          style: FilledButton.styleFrom(backgroundColor: color, padding: EdgeInsets.symmetric(horizontal: rp(context, 16))),
          child: Text('Начать', style: TextStyle(fontSize: rs(context, 14)))),
      ]));
  }
}

class _ResultStat extends StatelessWidget {
  const _ResultStat({required this.label, required this.value, required this.color});
  final String label, value;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(rp(context, 16)),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(14)),
      child: Column(children: [
        Text(value, style: TextStyle(fontSize: rs(context, 22), fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: rs(context, 12), color: Colors.grey[600])),
      ]));
  }
}

class _TopicList extends StatelessWidget {
  const _TopicList({required this.title, required this.topics, required this.color});
  final String title;
  final List topics;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity, margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 4)]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        const SizedBox(height: 8),
        ...topics.map((t) {
          final name = t is Map ? (t['name'] ?? t['node_name'] ?? '$t') : '$t';
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(children: [
              Container(width: 6, height: 6,
                decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
              const SizedBox(width: 8),
              Text('$name', style: const TextStyle(fontSize: 13)),
            ]));
        }),
      ]));
  }
}
