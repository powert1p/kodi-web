import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../shared/widgets/problem_card.dart';
import '../../../shared/widgets/answer_input.dart';
import '../../../shared/widgets/result_card.dart';
import '../../../shared/widgets/report_sheet.dart';
import '../../../shared/utils/responsive.dart';

class PracticePage extends StatefulWidget {
  const PracticePage({super.key, this.tag, this.tagName, this.nodeId, this.embedded = false});
  final String? tag;
  final String? tagName;
  final String? nodeId;
  final bool embedded;
  static const routeName = '/practice';
  @override
  State<PracticePage> createState() => _PracticePageState();
}

class _PracticePageState extends State<PracticePage> with TickerProviderStateMixin {
  late final NisApiClient _api;
  Problem? _problem;
  AnswerResult? _result;
  bool _loading = true;
  int _count = 1;
  int _correct = 0;
  int _combo = 0;
  int _bestCombo = 0;
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _scrollController = ScrollController();
  final _keyboardFocus = FocusNode();

  late Stopwatch _stopwatch;
  Timer? _tickTimer;
  int _elapsedSeconds = 0;
  double _totalTimeSpent = 0;

  late AnimationController _resultAnimController;
  late Animation<double> _resultFadeIn;
  late AnimationController _comboAnimController;

  @override
  void initState() {
    super.initState();
    _api = context.read<NisApiClient>();
    _stopwatch = Stopwatch();
    _resultAnimController = AnimationController(vsync: this, duration: const Duration(milliseconds: 400));
    _resultFadeIn = CurvedAnimation(parent: _resultAnimController, curve: Curves.easeOut);
    _comboAnimController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _loadNext();
  }

  @override
  void dispose() {
    _tickTimer?.cancel();
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    _scrollController.dispose();
    _resultAnimController.dispose();
    _comboAnimController.dispose();
    super.dispose();
  }

  Future<void> _loadNext() async {
    setState(() { _loading = true; _result = null; _controller.clear(); });
    try {
      final p = await _api.getNextProblem(count: _count, tag: widget.tag, nodeId: widget.nodeId);
      setState(() { _problem = p; _loading = false; });
      _resultAnimController.reset();
      _startTimer();
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _focusNode.requestFocus();
          _scrollController.animateTo(0, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
        }
      });
    } on NetworkException catch (e) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } on ApiException catch (e) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } catch (_) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Не удалось загрузить задачу')));
    }
  }

  void _startTimer() {
    _stopwatch.reset(); _stopwatch.start(); _elapsedSeconds = 0;
    _tickTimer?.cancel();
    _tickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSeconds = _stopwatch.elapsed.inSeconds);
    });
  }

  void _stopTimer() {
    _stopwatch.stop(); _tickTimer?.cancel();
    _totalTimeSpent += _stopwatch.elapsed.inMilliseconds / 1000.0;
  }

  Future<void> _submit() async {
    final answer = _controller.text.trim();
    if (_problem == null || answer.isEmpty) return;
    _stopTimer();
    setState(() => _loading = true);
    try {
      final res = await _api.submitAnswer(_problem!.problemId, answer);
      setState(() {
        _result = res; _loading = false; _count++;
        if (res.isCorrect) {
          _correct++; _combo++;
          if (_combo > _bestCombo) _bestCombo = _combo;
          if (_combo >= 3) _comboAnimController.forward(from: 0);
        } else { _combo = 0; }
      });
      _resultAnimController.forward();
    } on NetworkException catch (e) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } on ApiException catch (e) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } catch (_) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Не удалось отправить ответ')));
    }
  }

  Future<void> _skip() async {
    if (_problem == null) return;
    _stopTimer(); _combo = 0;
    await _api.skipProblem(_problem!.problemId);
    _count++; await _loadNext();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    if (_result != null && (event.logicalKey == LogicalKeyboardKey.arrowRight || event.logicalKey == LogicalKeyboardKey.space)) {
      _loadNext();
    }
  }

  String _fmtTime(int s) => s < 60 ? '${s}с' : '${s ~/ 60}м ${s % 60}с';
  String _fmtAvg() {
    if (_count <= 1) return '-';
    return '${(_totalTimeSpent / (_count - 1)).toStringAsFixed(1)}с';
  }

  void _showStats() {
    final n = _count - 1;
    final pct = n > 0 ? (_correct / n * 100).round() : 0;
    showModalBottomSheet(context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (sheetCtx) => Padding(padding: EdgeInsets.all(rp(sheetCtx, 24)), child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text('Статистика сессии', style: TextStyle(fontSize: rs(sheetCtx, 18), fontWeight: FontWeight.bold)),
        const SizedBox(height: 20),
        Row(children: [
          _StatTile(label: 'Решено', value: '$n', icon: Icons.check_circle_outline),
          _StatTile(label: 'Правильно', value: '$_correct', icon: Icons.thumb_up_outlined),
          _StatTile(label: 'Точность', value: '$pct%', icon: Icons.percent),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          _StatTile(label: 'Ср. время', value: _fmtAvg(), icon: Icons.timer_outlined),
          _StatTile(label: 'Макс комбо', value: '$_bestCombo 🔥', icon: Icons.local_fire_department),
          _StatTile(label: 'Всего', value: _fmtTime(_totalTimeSpent.round()), icon: Icons.schedule),
        ]),
        const SizedBox(height: 20),
        SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(sheetCtx), child: const Text('Продолжить'))),
      ])));
  }

  Future<bool> _confirmLeave() async {
    if (_count <= 2) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Завершить практику?'),
        content: Text('Решено задач: ${_count - 1}, правильно: $_correct.'),
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

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _count <= 2,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldLeave = await _confirmLeave();
        if (shouldLeave && context.mounted) Navigator.of(context).pop();
      },
      child: KeyboardListener(
        focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
        child: Scaffold(
          backgroundColor: const Color(0xFFFAF9F6),
          appBar: AppBar(
            backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
            leading: BackButton(onPressed: () async {
              if (_count <= 2) { Navigator.of(context).pop(); return; }
              final shouldLeave = await _confirmLeave();
              if (shouldLeave && context.mounted) Navigator.of(context).pop();
            }),
          title: Row(children: [
            Flexible(child: Text(widget.tagName ?? 'Практика',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17), overflow: TextOverflow.ellipsis)),
            const Spacer(),
            if (_result == null && !_loading)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _elapsedSeconds > 120 ? const Color(0xFFFEF2F2) : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(12)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.timer_outlined, size: 14,
                    color: _elapsedSeconds > 120 ? const Color(0xFFEF4444) : Colors.grey[500]),
                  const SizedBox(width: 3),
                  Text(_fmtTime(_elapsedSeconds), style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
                    color: _elapsedSeconds > 120 ? const Color(0xFFEF4444) : Colors.grey[500],
                    fontFeatures: const [FontFeature.tabularFigures()])),
                ])),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: const Color(0xFFECFDF5), borderRadius: BorderRadius.circular(20)),
              child: Text(_count > 1 ? '$_correct/${_count - 1}' : '0/0',
                style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.w600))),
          ]),
          actions: [
            if (_count > 2) IconButton(icon: const Icon(Icons.assessment_rounded, color: Color(0xFF64748B)),
              onPressed: _showStats, tooltip: 'Статистика'),
          ]),
          body: _loading ? const Center(child: CircularProgressIndicator())
            : Align(alignment: Alignment.topCenter,
                child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                  child: SingleChildScrollView(controller: _scrollController,
                    padding: const EdgeInsets.all(16), child: _buildContent()))),
        )),
    );
  }

  Widget _buildContent() {
    final p = _problem;
    if (p == null) {
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

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      // Combo banner
      if (_combo >= 3)
        ScaleTransition(
          scale: Tween(begin: 0.8, end: 1.0).animate(_comboAnimController),
          child: Container(
            width: double.infinity, padding: const EdgeInsets.symmetric(vertical: 8),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFFF6B35), Color(0xFFFF8F00)]),
              borderRadius: BorderRadius.circular(12)),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              const Text('🔥', style: TextStyle(fontSize: 18)),
              const SizedBox(width: 6),
              Text('$_combo подряд!', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
            ]))),

      // Problem card (shared widget)
      ProblemCard(
        text: p.text,
        nodeName: p.nodeName,
        difficulty: p.difficulty,
        counter: '#$_count'),
      const SizedBox(height: 16),

      // Result (animated) or Input
      if (_result != null)
        FadeTransition(opacity: _resultFadeIn,
          child: SlideTransition(
            position: Tween(begin: const Offset(0, 0.1), end: Offset.zero).animate(_resultFadeIn),
            child: Column(children: [
              ResultCard(
                isCorrect: _result!.isCorrect,
                correctAnswer: _result!.isCorrect ? null : _result!.correctAnswer,
                solution: _result!.solution,
                pMastery: _result!.pMastery,
                isMastered: _result!.isMastered,
                nodeName: p.nodeName,
                onReport: !_result!.isCorrect ? () => showReportSheet(context, _api, p.problemId) : null),
              const SizedBox(height: 16),
              SizedBox(width: double.infinity, child: FilledButton.icon(
                onPressed: _loadNext,
                icon: const Icon(Icons.arrow_forward_rounded),
                label: const Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Следующая', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  SizedBox(width: 8),
                  Text('→', style: TextStyle(fontSize: 14, color: Colors.white70)),
                ]),
                style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: const Color(0xFF2563EB)))),
              const SizedBox(height: 8),
              Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
            ])))
      else
        AnswerInput(
          controller: _controller,
          focusNode: _focusNode,
          onSubmit: _submit,
          onSkip: _skip,
          onReport: () => showReportSheet(context, _api, p.problemId)),
    ]);
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, required this.icon});
  final String label, value;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Expanded(child: Column(children: [
    Icon(icon, size: rs(context, 22), color: const Color(0xFF64748B)),
    const SizedBox(height: 6),
    Text(value, style: TextStyle(fontSize: rs(context, 18), fontWeight: FontWeight.bold)),
    Text(label, style: TextStyle(fontSize: rs(context, 11), color: Colors.grey[500])),
  ]));
}
