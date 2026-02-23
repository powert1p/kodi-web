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

class ExamPage extends StatefulWidget {
  const ExamPage({super.key});
  static const routeName = '/exam';
  @override
  State<ExamPage> createState() => _ExamPageState();
}

class _ExamPageState extends State<ExamPage> {
  late final NisApiClient _api;
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _keyboardFocus = FocusNode();

  bool _loading = false;
  bool _started = false;
  bool _finished = false;
  String? _error;

  int _numProblems = 20;
  int _timeMinutes = 40;

  List<Map<String, dynamic>> _problems = [];
  int _currentIndex = 0;
  Map<String, dynamic>? _answerResult;

  int _secondsLeft = 0;
  Timer? _timer;

  int _correct = 0;
  int _answered = 0;
  final Map<int, bool> _results = {};

  @override
  void initState() {
    super.initState();
    _api = context.read<NisApiClient>();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    super.dispose();
  }

  Future<void> _startExam() async {
    setState(() { _loading = true; _error = null; });
    try {
      final resp = await _api.post('/api/practice/exam/start', {
        'num_problems': _numProblems, 'time_minutes': _timeMinutes});
      final problems = (resp['problems'] as List).cast<Map<String, dynamic>>();
      setState(() {
        _problems = problems; _started = true; _loading = false;
        _currentIndex = 0; _correct = 0; _answered = 0;
        _results.clear(); _answerResult = null;
        _secondsLeft = _timeMinutes * 60;
      });
      _startTimer();
      _focusAnswer();
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось запустить экзамен'; });
    }
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_secondsLeft <= 0) { t.cancel(); _finishExam(); return; }
      setState(() => _secondsLeft--);
    });
  }

  void _focusAnswer() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focusNode.requestFocus();
    });
  }

  Future<void> _submitAnswer() async {
    final answer = _controller.text.trim();
    if (answer.isEmpty || _currentIndex >= _problems.length) return;
    final problem = _problems[_currentIndex];
    setState(() => _loading = true);
    try {
      final result = await _api.post('/api/practice/answer', {
        'problem_id': problem['problem_id'], 'answer': answer});
      final isCorrect = result['is_correct'] == true;
      _results[problem['problem_id']] = isCorrect;
      if (isCorrect) _correct++;
      _answered++;
      setState(() { _answerResult = result; _loading = false; });
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось отправить ответ'; });
    }
  }

  void _nextProblem() {
    if (_currentIndex + 1 >= _problems.length) { _finishExam(); return; }
    setState(() { _currentIndex++; _answerResult = null; _controller.clear(); });
    _focusAnswer();
  }

  void _skipProblem() {
    _answered++;
    _results[_problems[_currentIndex]['problem_id']] = false;
    _nextProblem();
  }

  void _finishExam() {
    _timer?.cancel();
    setState(() { _finished = true; _started = false; });
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    if (_answerResult != null &&
        (event.logicalKey == LogicalKeyboardKey.arrowRight ||
         event.logicalKey == LogicalKeyboardKey.space)) {
      _nextProblem();
    }
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  Future<bool> _confirmLeave() async {
    if (!_started || _finished) return true;
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
            style: TextButton.styleFrom(foregroundColor: const Color(0xFFEF4444)),
            child: const Text('Выйти')),
        ],
      ),
    );
    return leave ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_started || _finished,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldLeave = await _confirmLeave();
        if (shouldLeave && context.mounted) {
          _timer?.cancel();
          Navigator.of(context).pop();
        }
      },
      child: KeyboardListener(
        focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
        child: Scaffold(
          backgroundColor: const Color(0xFFFAF9F6),
          appBar: AppBar(
            backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
            leading: BackButton(onPressed: () async {
              if (!_started || _finished) { Navigator.of(context).pop(); return; }
              final shouldLeave = await _confirmLeave();
              if (shouldLeave && context.mounted) {
                _timer?.cancel();
                Navigator.of(context).pop();
              }
            }),
            title: Row(children: [
              const Text('Экзамен', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              if (_started) ...[
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Text('${_currentIndex + 1}/${_problems.length}',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey[500]))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: _secondsLeft < 300 ? const Color(0xFFFEF2F2) : const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(20)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.timer_rounded, size: 16,
                      color: _secondsLeft < 300 ? const Color(0xFFEF4444) : const Color(0xFF2563EB)),
                    const SizedBox(width: 4),
                    Text(_formatTime(_secondsLeft),
                      style: TextStyle(
                        color: _secondsLeft < 300 ? const Color(0xFFEF4444) : const Color(0xFF2563EB),
                        fontSize: 14, fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()])),
                  ])),
              ],
            ])),
          body: _loading ? const Center(child: CircularProgressIndicator())
            : Align(alignment: Alignment.topCenter,
                child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                  child: SingleChildScrollView(padding: const EdgeInsets.all(16), child: _buildContent()))),
        )),
    );
  }

  Widget _buildContent() {
    if (_error != null) return _buildError();
    if (_finished) return _buildResults();
    if (!_started) return _buildSetup();
    if (_answerResult != null) return _buildAnswerFeedback();
    return _buildQuestion();
  }

  Widget _buildSetup() {
    return Column(children: [
      const SizedBox(height: 40),
      Container(width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFFEF4444), Color(0xFFF97316)]),
          borderRadius: BorderRadius.circular(20)),
        child: Icon(Icons.timer_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text('Экзамен', style: TextStyle(fontSize: rs(context, 24), fontWeight: FontWeight.bold, color: const Color(0xFF1E293B))),
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
            Icon(Icons.assignment_rounded, size: rs(context, 20), color: const Color(0xFF64748B)),
            const SizedBox(width: 8), Text('Задач:', style: TextStyle(fontSize: rs(context, 14))), const Spacer(),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 10, label: Text('10')),
                ButtonSegment(value: 20, label: Text('20')),
                ButtonSegment(value: 30, label: Text('30'))],
              selected: {_numProblems},
              onSelectionChanged: (v) => setState(() { _numProblems = v.first; _timeMinutes = v.first * 2; }),
              style: SegmentedButton.styleFrom(
                selectedBackgroundColor: const Color(0xFF2563EB), selectedForegroundColor: Colors.white)),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            const Icon(Icons.timer_rounded, size: 20, color: Color(0xFF64748B)),
            const SizedBox(width: 8), const Text('Время:'), const Spacer(),
            Text('$_timeMinutes мин', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
          ]),
        ])),
      const SizedBox(height: 24),
      SizedBox(width: double.infinity, child: FilledButton.icon(
        onPressed: _startExam,
        icon: const Icon(Icons.play_arrow_rounded),
        label: const Text('Начать экзамен', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: const Color(0xFFEF4444)))),
    ]);
  }

  Widget _buildQuestion() {
    final p = _problems[_currentIndex];
    final text = p['text'] as String? ?? '';
    final nodeName = p['node_name'] as String?;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: _problems.isNotEmpty ? (_currentIndex + 1) / _problems.length : 0,
          minHeight: 6,
          backgroundColor: const Color(0xFFE2E8F0),
          valueColor: const AlwaysStoppedAnimation(Color(0xFFEF4444)))),
      const SizedBox(height: 4),
      Row(children: [
        Text('Задача ${_currentIndex + 1} из ${_problems.length}',
          style: TextStyle(fontSize: 12, color: Colors.grey[500])),
        const Spacer(),
        Text('$_correct правильно',
          style: const TextStyle(fontSize: 12, color: Color(0xFF10B981), fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 16),

      ProblemCard(text: text, nodeName: nodeName),
      const SizedBox(height: 16),

      AnswerInput(
        controller: _controller, focusNode: _focusNode,
        onSubmit: _submitAnswer, onSkip: _skipProblem,
        onReport: () => showReportSheet(context, _api, p['problem_id']),
        accentColor: const Color(0xFFEF4444)),
    ]);
  }

  Widget _buildAnswerFeedback() {
    final r = _answerResult!;
    final ok = r['is_correct'] == true;
    final isLast = _currentIndex + 1 >= _problems.length;

    return Column(children: [
      ResultCard(
        isCorrect: ok,
        correctAnswer: r['correct_answer']?.toString(),
        solution: r['solution'] as String?,
        nodeName: _problems[_currentIndex]['node_name'] as String?,
        onReport: !ok ? () => showReportSheet(context, _api, _problems[_currentIndex]['problem_id']) : null),
      const SizedBox(height: 16),
      SizedBox(width: double.infinity, child: FilledButton(
        onPressed: _nextProblem,
        style: FilledButton.styleFrom(minimumSize: const Size(0, 48), backgroundColor: const Color(0xFF2563EB)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(isLast ? 'Завершить' : 'Следующая →',
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        ]))),
      const SizedBox(height: 8),
      Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
    ]);
  }

  Widget _buildResults() {
    final total = _problems.length;
    final pct = total > 0 ? (_correct / total * 100).round() : 0;
    final timeUsed = _timeMinutes * 60 - _secondsLeft;

    return Column(children: [
      const SizedBox(height: 20),
      Container(width: rs(context, 80), height: rs(context, 80),
        decoration: BoxDecoration(
          color: pct >= 70 ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
          borderRadius: BorderRadius.circular(20)),
        child: Icon(pct >= 70 ? Icons.emoji_events_rounded : Icons.assessment_rounded, color: Colors.white, size: rs(context, 44))),
      const SizedBox(height: 24),
      Text(pct >= 70 ? 'Отлично!' : 'Можно лучше!',
        style: TextStyle(fontSize: rs(context, 22), fontWeight: FontWeight.bold, color: const Color(0xFF1E293B))),
      const SizedBox(height: 8),
      Text('Время: ${_formatTime(timeUsed)}',
        style: TextStyle(fontSize: rs(context, 15), color: Colors.grey[600])),
      const SizedBox(height: 24),
      Row(children: [
        Expanded(child: _StatCard(label: 'Результат', value: '$pct%',
          color: pct >= 70 ? const Color(0xFF10B981) : const Color(0xFFF59E0B))),
        const SizedBox(width: 10),
        Expanded(child: _StatCard(label: 'Правильно', value: '$_correct/$total', color: const Color(0xFF2563EB))),
        const SizedBox(width: 10),
        Expanded(child: _StatCard(label: 'Пропущено', value: '${total - _answered}', color: const Color(0xFF64748B))),
      ]),
      const SizedBox(height: 24),
      SizedBox(width: double.infinity, child: FilledButton.icon(
        onPressed: () => setState(() { _finished = false; _started = false; _problems.clear(); }),
        icon: const Icon(Icons.refresh_rounded),
        label: const Text('Ещё раз', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        style: FilledButton.styleFrom(minimumSize: const Size(0, 52), backgroundColor: const Color(0xFFEF4444)))),
      const SizedBox(height: 12),
      SizedBox(width: double.infinity, child: OutlinedButton.icon(
        onPressed: () => Navigator.of(context).pop(),
        icon: const Icon(Icons.home_rounded),
        label: const Text('На главную', style: TextStyle(fontSize: 16)),
        style: OutlinedButton.styleFrom(minimumSize: const Size(0, 52)))),
    ]);
  }

  Widget _buildError() {
    return Column(children: [
      const SizedBox(height: 40),
      Icon(Icons.error_outline, size: 48, color: Colors.red[300]),
      const SizedBox(height: 16),
      Text('Что-то пошло не так', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.grey[700])),
      const SizedBox(height: 8),
      Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey[500], fontSize: 13)),
      const SizedBox(height: 16),
      FilledButton(onPressed: () => setState(() => _error = null), child: const Text('Назад')),
    ]);
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
