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
import '../bloc/practice_bloc.dart';

class PracticePage extends StatefulWidget {
  const PracticePage({super.key, this.tagName, this.embedded = false});
  final String? tagName;
  final bool embedded;
  static const routeName = '/practice';
  @override
  State<PracticePage> createState() => _PracticePageState();
}

class _PracticePageState extends State<PracticePage> with TickerProviderStateMixin {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _scrollController = ScrollController();
  final _keyboardFocus = FocusNode();

  late AnimationController _resultAnimController;
  late Animation<double> _resultFadeIn;
  late AnimationController _comboAnimController;

  @override
  void initState() {
    super.initState();
    _resultAnimController = AnimationController(vsync: this, duration: const Duration(milliseconds: 400));
    _resultFadeIn = CurvedAnimation(parent: _resultAnimController, curve: Curves.easeOut);
    _comboAnimController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    _scrollController.dispose();
    _resultAnimController.dispose();
    _comboAnimController.dispose();
    super.dispose();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    final state = context.read<PracticeBloc>().state;
    if (state is PracticeAnswerShown &&
        (event.logicalKey == LogicalKeyboardKey.arrowRight ||
         event.logicalKey == LogicalKeyboardKey.space)) {
      context.read<PracticeBloc>().add(PracticeNextRequested());
    }
  }

  String _fmtTime(int s) => s < 60 ? '${s}с' : '${s ~/ 60}м ${s % 60}с';
  String _fmtAvg(double totalTime, int count) {
    if (count <= 1) return '-';
    return '${(totalTime / (count - 1)).toStringAsFixed(1)}с';
  }

  void _showStats(PracticeState state) {
    final int count;
    final int correct;
    final int bestCombo;
    final double totalTime;
    if (state is PracticeProblemReady) {
      count = state.count; correct = state.correct;
      bestCombo = state.bestCombo; totalTime = state.totalTimeSpent;
    } else if (state is PracticeAnswerShown) {
      count = state.count; correct = state.correct;
      bestCombo = state.bestCombo; totalTime = state.totalTimeSpent;
    } else {
      return;
    }

    final n = count - 1;
    final pct = n > 0 ? (correct / n * 100).round() : 0;
    showModalBottomSheet(context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (sheetCtx) => Padding(padding: EdgeInsets.all(rp(sheetCtx, 24)), child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text('Статистика сессии', style: TextStyle(fontSize: rs(sheetCtx, 18), fontWeight: FontWeight.bold)),
        const SizedBox(height: 20),
        Row(children: [
          _StatTile(label: 'Решено', value: '$n', icon: Icons.check_circle_outline),
          _StatTile(label: 'Правильно', value: '$correct', icon: Icons.thumb_up_outlined),
          _StatTile(label: 'Точность', value: '$pct%', icon: Icons.percent),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          _StatTile(label: 'Ср. время', value: _fmtAvg(totalTime, count), icon: Icons.timer_outlined),
          _StatTile(label: 'Макс комбо', value: '$bestCombo 🔥', icon: Icons.local_fire_department),
          _StatTile(label: 'Всего', value: _fmtTime(totalTime.round()), icon: Icons.schedule),
        ]),
        const SizedBox(height: 20),
        SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(sheetCtx), child: const Text('Продолжить'))),
      ])));
  }

  Future<bool> _confirmLeave(int count) async {
    if (count <= 2) return true;
    final state = context.read<PracticeBloc>().state;
    final correct = state is PracticeProblemReady ? state.correct
        : state is PracticeAnswerShown ? state.correct : 0;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Завершить практику?'),
        content: Text('Решено задач: ${count - 1}, правильно: $correct.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Продолжить')),
          TextButton(onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Выйти')),
        ],
      ),
    );
    return leave ?? false;
  }

  int _currentCount(PracticeState state) {
    if (state is PracticeProblemReady) return state.count;
    if (state is PracticeAnswerShown) return state.count;
    return 1;
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<PracticeBloc, PracticeState>(
      listener: (context, state) {
        if (state is PracticeProblemReady) {
          _resultAnimController.reset();
          _controller.clear();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _focusNode.requestFocus();
              _scrollController.animateTo(0, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
            }
          });
        }
        if (state is PracticeAnswerShown) {
          _resultAnimController.forward();
          if (state.combo >= 3) _comboAnimController.forward(from: 0);
        }
        if (state is PracticeError) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.message)));
        }
      },
      builder: (context, state) {
        final count = _currentCount(state);
        return PopScope(
          canPop: count <= 2,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final shouldLeave = await _confirmLeave(count);
            if (shouldLeave && context.mounted) Navigator.of(context).pop();
          },
          child: KeyboardListener(
            focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
            child: Scaffold(
              backgroundColor: AppColors.scaffoldBg,
              appBar: _buildAppBar(context, state, count),
              body: state is PracticeLoading
                  ? const Center(child: CircularProgressIndicator())
                  : Align(alignment: Alignment.topCenter,
                      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                        child: SingleChildScrollView(controller: _scrollController,
                          padding: const EdgeInsets.all(16), child: _buildContent(context, state)))),
            )),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context, PracticeState state, int count) {
    final int elapsedSeconds;
    final bool showTimer;
    final int correct;
    if (state is PracticeProblemReady) {
      elapsedSeconds = state.elapsedSeconds;
      showTimer = true;
      correct = state.correct;
    } else if (state is PracticeAnswerShown) {
      elapsedSeconds = 0;
      showTimer = false;
      correct = state.correct;
    } else {
      elapsedSeconds = 0;
      showTimer = false;
      correct = 0;
    }

    return AppBar(
      backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
      leading: BackButton(onPressed: () async {
        if (count <= 2) { Navigator.of(context).pop(); return; }
        final shouldLeave = await _confirmLeave(count);
        if (shouldLeave && context.mounted) Navigator.of(context).pop();
      }),
      title: Row(children: [
        Flexible(child: Text(widget.tagName ?? 'Практика',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17), overflow: TextOverflow.ellipsis)),
        const Spacer(),
        if (showTimer)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: elapsedSeconds > 120 ? AppColors.errorBgLight : AppColors.surface,
              borderRadius: BorderRadius.circular(12)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.timer_outlined, size: 14,
                color: elapsedSeconds > 120 ? AppColors.error : Colors.grey[500]),
              const SizedBox(width: 3),
              Text(_fmtTime(elapsedSeconds), style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
                color: elapsedSeconds > 120 ? AppColors.error : Colors.grey[500],
                fontFeatures: const [FontFeature.tabularFigures()])),
            ])),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(color: AppColors.successBgLight, borderRadius: BorderRadius.circular(20)),
          child: Text(count > 1 ? '$correct/${count - 1}' : '0/0',
            style: const TextStyle(color: AppColors.success, fontSize: 13, fontWeight: FontWeight.w600))),
      ]),
      actions: [
        if (count > 2) IconButton(icon: const Icon(Icons.assessment_rounded, color: AppColors.textSecondary),
          onPressed: () => _showStats(state), tooltip: 'Статистика'),
      ]);
  }

  Widget _buildContent(BuildContext context, PracticeState state) {
    if (state is PracticeAllDone || state is PracticeError) {
      return Column(children: [
        const SizedBox(height: 60),
        Icon(Icons.emoji_events_rounded, size: 64, color: Colors.amber[400]),
        const SizedBox(height: 16),
        const Text('Все задачи решены! 🎉', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text('Попробуй другую тему', style: TextStyle(color: Colors.grey[500])),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => Navigator.pop(context), child: const Text('На главную')),
      ]);
    }

    final Problem? problem;
    final AnswerResult? result;
    final int combo;
    if (state is PracticeProblemReady) {
      problem = state.problem; result = null; combo = state.combo;
    } else if (state is PracticeAnswerShown) {
      problem = state.problem; result = state.result; combo = state.combo;
    } else {
      return const SizedBox.shrink();
    }

    final p = problem;
    final bloc = context.read<PracticeBloc>();
    final api = context.read<NisApiClient>();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      // Combo banner
      if (combo >= 3)
        ScaleTransition(
          scale: Tween(begin: 0.8, end: 1.0).animate(_comboAnimController),
          child: Container(
            width: double.infinity, padding: const EdgeInsets.symmetric(vertical: 8),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [AppColors.comboStart, AppColors.comboEnd]),
              borderRadius: BorderRadius.circular(12)),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              const Text('🔥', style: TextStyle(fontSize: 18)),
              const SizedBox(width: 6),
              Text('$combo подряд!', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
            ]))),

      ProblemCard(
        text: p.text,
        nodeName: p.nodeName,
        difficulty: p.difficulty,
        counter: '#${_currentCount(state)}'),
      const SizedBox(height: 16),

      if (result != null)
        FadeTransition(opacity: _resultFadeIn,
          child: SlideTransition(
            position: Tween(begin: const Offset(0, 0.1), end: Offset.zero).animate(_resultFadeIn),
            child: Column(children: [
              ResultCard(
                isCorrect: result.isCorrect,
                correctAnswer: result.isCorrect ? null : result.correctAnswer,
                solution: result.solution,
                pMastery: result.pMastery,
                isMastered: result.isMastered,
                nodeName: p.nodeName,
                onReport: !result.isCorrect ? () => showReportSheet(context, api, p.problemId) : null),
              const SizedBox(height: 16),
              SizedBox(width: double.infinity, child: FilledButton.icon(
                onPressed: () => bloc.add(PracticeNextRequested()),
                icon: const Icon(Icons.arrow_forward_rounded),
                label: const Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Следующая', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  SizedBox(width: 8),
                  Text('→', style: TextStyle(fontSize: 14, color: Colors.white70)),
                ]),
                style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: AppColors.primary))),
              const SizedBox(height: 8),
              Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
            ])))
      else
        AnswerInput(
          controller: _controller,
          focusNode: _focusNode,
          onSubmit: () => bloc.add(PracticeAnswerSubmitted(_controller.text.trim())),
          onSkip: () => bloc.add(PracticeProblemSkipped()),
          onReport: () => showReportSheet(context, api, p.problemId)),
    ]);
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, required this.icon});
  final String label, value;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Expanded(child: Column(children: [
    Icon(icon, size: rs(context, 22), color: AppColors.textSecondary),
    const SizedBox(height: 6),
    Text(value, style: TextStyle(fontSize: rs(context, 18), fontWeight: FontWeight.bold)),
    Text(label, style: TextStyle(fontSize: rs(context, 11), color: Colors.grey[500])),
  ]));
}
