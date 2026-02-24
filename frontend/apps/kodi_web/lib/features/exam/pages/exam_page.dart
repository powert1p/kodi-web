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
import '../bloc/exam_bloc.dart';

class ExamPage extends StatefulWidget {
  const ExamPage({super.key});
  static const routeName = '/exam';
  @override
  State<ExamPage> createState() => _ExamPageState();
}

class _ExamPageState extends State<ExamPage> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _keyboardFocus = FocusNode();

  // Setup state (before exam starts — UI-only)
  int _numProblems = 20;
  int _timeMinutes = 40;

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    super.dispose();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    final state = context.read<ExamBloc>().state;
    if (state is ExamAnswerShown &&
        (event.logicalKey == LogicalKeyboardKey.arrowRight ||
         event.logicalKey == LogicalKeyboardKey.space)) {
      context.read<ExamBloc>().add(ExamNextProblemRequested());
    }
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  Future<bool> _confirmLeave(ExamState state) async {
    final isActive = state is ExamQuestionReady || state is ExamAnswerShown;
    if (!isActive) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Покинуть экзамен?'),
        content: const Text(
          'Таймер идёт! Если выйдешь, прогресс будет потерян.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Остаться')),
          TextButton(onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Выйти')),
        ],
      ),
    );
    return leave ?? false;
  }

  bool _isExamActive(ExamState state) =>
      state is ExamQuestionReady || state is ExamAnswerShown;

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ExamBloc, ExamState>(
      listener: (context, state) {
        if (state is ExamQuestionReady) {
          _controller.clear();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _focusNode.requestFocus();
          });
        }
        if (state is ExamError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.message)));
        }
      },
      builder: (context, state) {
        final canPop = !_isExamActive(state) && state is! ExamLoading;
        return PopScope(
          canPop: canPop,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final shouldLeave = await _confirmLeave(state);
            if (shouldLeave && context.mounted) Navigator.of(context).pop();
          },
          child: KeyboardListener(
            focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
            child: Scaffold(
              backgroundColor: AppColors.scaffoldBg,
              appBar: _buildAppBar(context, state),
              body: state is ExamLoading
                  ? const Center(child: CircularProgressIndicator())
                  : Align(alignment: Alignment.topCenter,
                      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                        child: SingleChildScrollView(padding: const EdgeInsets.all(16), child: _buildContent(context, state)))),
            )),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context, ExamState state) {
    return AppBar(
      backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
      leading: BackButton(onPressed: () async {
        if (!_isExamActive(state)) { Navigator.of(context).pop(); return; }
        final shouldLeave = await _confirmLeave(state);
        if (shouldLeave && context.mounted) Navigator.of(context).pop();
      }),
      title: Row(children: [
        const Text('Экзамен', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        if (state is ExamQuestionReady) ...[
          const Spacer(),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Text('${state.currentIndex + 1}/${state.problems.length}',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey[500]))),
          _TimerBadge(secondsLeft: state.secondsLeft, formatTime: _formatTime),
        ],
        if (state is ExamAnswerShown) ...[
          const Spacer(),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Text('${state.currentIndex + 1}/${state.problems.length}',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey[500]))),
          _TimerBadge(secondsLeft: state.secondsLeft, formatTime: _formatTime),
        ],
      ]));
  }

  Widget _buildContent(BuildContext context, ExamState state) {
    return switch (state) {
      ExamError(:final message) => _buildError(context, message),
      ExamFinished() => _buildResults(context, state),
      ExamInitial() => _buildSetup(context),
      ExamQuestionReady() => _buildQuestion(context, state),
      ExamAnswerShown() => _buildAnswerFeedback(context, state),
      _ => const SizedBox.shrink(),
    };
  }

  Widget _buildSetup(BuildContext context) {
    return Column(children: [
      const SizedBox(height: 40),
      Container(width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [AppColors.error, AppColors.orangeGradient]),
          borderRadius: BorderRadius.circular(20)),
        child: Icon(Icons.timer_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text('Экзамен', style: TextStyle(fontSize: rs(context, 24), fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
      const SizedBox(height: 8),
      Text('Реши задачи на время — как на настоящем НИШ',
        style: TextStyle(fontSize: rs(context, 15), color: Colors.grey[600]), textAlign: TextAlign.center),
      const SizedBox(height: 32),
      Container(
        width: double.infinity, padding: EdgeInsets.all(rp(context, 20)),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Настройки', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
          const SizedBox(height: 16),
          Row(children: [
            Icon(Icons.assignment_rounded, size: rs(context, 20), color: AppColors.textSecondary),
            const SizedBox(width: 8), Text('Задач:', style: TextStyle(fontSize: rs(context, 14))), const Spacer(),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 10, label: Text('10')),
                ButtonSegment(value: 20, label: Text('20')),
                ButtonSegment(value: 30, label: Text('30'))],
              selected: {_numProblems},
              onSelectionChanged: (v) => setState(() { _numProblems = v.first; _timeMinutes = v.first * 2; }),
              style: SegmentedButton.styleFrom(
                selectedBackgroundColor: AppColors.primary, selectedForegroundColor: Colors.white)),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            const Icon(Icons.timer_rounded, size: 20, color: AppColors.textSecondary),
            const SizedBox(width: 8), const Text('Время:'), const Spacer(),
            Text('$_timeMinutes мин', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
          ]),
        ])),
      const SizedBox(height: 24),
      SizedBox(width: double.infinity, child: FilledButton.icon(
        onPressed: () => context.read<ExamBloc>().add(
            ExamStartRequested(numProblems: _numProblems, timeMinutes: _timeMinutes)),
        icon: const Icon(Icons.play_arrow_rounded),
        label: const Text('Начать экзамен', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: AppColors.error))),
    ]);
  }

  Widget _buildQuestion(BuildContext context, ExamQuestionReady state) {
    final p = state.problems[state.currentIndex];
    final text = p['text'] as String? ?? '';
    final nodeName = p['node_name'] as String?;
    final bloc = context.read<ExamBloc>();
    final api = context.read<NisApiClient>();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: state.problems.isNotEmpty ? (state.currentIndex + 1) / state.problems.length : 0,
          minHeight: 6,
          backgroundColor: AppColors.border,
          valueColor: const AlwaysStoppedAnimation(AppColors.error))),
      const SizedBox(height: 4),
      Row(children: [
        Text('Задача ${state.currentIndex + 1} из ${state.problems.length}',
          style: TextStyle(fontSize: 12, color: Colors.grey[500])),
        const Spacer(),
        Text('${state.correct} правильно',
          style: const TextStyle(fontSize: 12, color: AppColors.success, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 16),

      ProblemCard(text: text, nodeName: nodeName),
      const SizedBox(height: 16),

      AnswerInput(
        controller: _controller, focusNode: _focusNode,
        onSubmit: () => bloc.add(ExamAnswerSubmitted(_controller.text.trim())),
        onSkip: () => bloc.add(ExamProblemSkipped()),
        onReport: () => showReportSheet(context, api, p['problem_id']),
        accentColor: AppColors.error),
    ]);
  }

  Widget _buildAnswerFeedback(BuildContext context, ExamAnswerShown state) {
    final r = state.answerResult;
    final ok = r['is_correct'] == true;
    final isLast = state.currentIndex + 1 >= state.problems.length;
    final bloc = context.read<ExamBloc>();
    final api = context.read<NisApiClient>();

    return Column(children: [
      ResultCard(
        isCorrect: ok,
        correctAnswer: r['correct_answer']?.toString(),
        solution: r['solution'] as String?,
        nodeName: state.problems[state.currentIndex]['node_name'] as String?,
        onReport: !ok ? () => showReportSheet(context, api, state.problems[state.currentIndex]['problem_id']) : null),
      const SizedBox(height: 16),
      SizedBox(width: double.infinity, child: FilledButton(
        onPressed: () => bloc.add(ExamNextProblemRequested()),
        style: FilledButton.styleFrom(minimumSize: const Size(0, 48), backgroundColor: AppColors.primary),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(isLast ? 'Завершить' : 'Следующая →',
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        ]))),
      const SizedBox(height: 8),
      Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
    ]);
  }

  Widget _buildResults(BuildContext context, ExamFinished state) {
    final pct = state.totalProblems > 0 ? (state.correct / state.totalProblems * 100).round() : 0;
    final bloc = context.read<ExamBloc>();

    return Column(children: [
      const SizedBox(height: 20),
      Container(width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          color: pct >= 70 ? AppColors.success : AppColors.warning,
          borderRadius: BorderRadius.circular(20)),
        child: Icon(pct >= 70 ? Icons.emoji_events_rounded : Icons.assessment_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text(pct >= 70 ? 'Отлично!' : 'Можно лучше!',
        style: TextStyle(fontSize: rs(context, 22), fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
      const SizedBox(height: 8),
      Text('Время: ${_formatTime(state.timeUsedSeconds)}',
        style: TextStyle(fontSize: rs(context, 15), color: Colors.grey[600])),
      const SizedBox(height: 24),
      Row(children: [
        Expanded(child: _StatCard(label: 'Результат', value: '$pct%',
          color: pct >= 70 ? AppColors.success : AppColors.warning)),
        const SizedBox(width: 10),
        Expanded(child: _StatCard(label: 'Правильно', value: '${state.correct}/${state.totalProblems}', color: AppColors.primary)),
        const SizedBox(width: 10),
        Expanded(child: _StatCard(label: 'Пропущено', value: '${state.totalProblems - state.answered}', color: AppColors.textSecondary)),
      ]),
      const SizedBox(height: 24),
      SizedBox(width: double.infinity, child: FilledButton.icon(
        onPressed: () => bloc.add(ExamResetRequested()),
        icon: const Icon(Icons.refresh_rounded),
        label: const Text('Ещё раз', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: AppColors.error))),
      const SizedBox(height: 12),
      SizedBox(width: double.infinity, child: OutlinedButton.icon(
        onPressed: () => Navigator.of(context).pop(),
        icon: const Icon(Icons.home_rounded),
        label: const Text('На главную', style: TextStyle(fontSize: 16)),
        style: OutlinedButton.styleFrom(minimumSize: const Size(0, 52)))),
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
      FilledButton(onPressed: () => context.read<ExamBloc>().add(ExamResetRequested()),
        child: const Text('Назад')),
    ]);
  }
}

class _TimerBadge extends StatelessWidget {
  const _TimerBadge({required this.secondsLeft, required this.formatTime});
  final int secondsLeft;
  final String Function(int) formatTime;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: secondsLeft < 300 ? AppColors.errorBgLight : AppColors.primaryBgLight,
        borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.timer_rounded, size: 16,
          color: secondsLeft < 300 ? AppColors.error : AppColors.primary),
        const SizedBox(width: 4),
        Text(formatTime(secondsLeft),
          style: TextStyle(
            color: secondsLeft < 300 ? AppColors.error : AppColors.primary,
            fontSize: 14, fontWeight: FontWeight.w700,
            fontFeatures: const [FontFeature.tabularFigures()])),
      ]));
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, required this.color});
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
