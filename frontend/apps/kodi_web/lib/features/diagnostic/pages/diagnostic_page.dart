import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../shared/widgets/problem_card.dart';
import '../../../shared/widgets/answer_input.dart';
import '../../../shared/widgets/result_card.dart';
import '../../../shared/widgets/report_sheet.dart';

class DiagnosticPage extends StatefulWidget {
  const DiagnosticPage({super.key});
  static const routeName = '/diagnostic';
  @override
  State<DiagnosticPage> createState() => _DiagnosticPageState();
}

class _DiagnosticPageState extends State<DiagnosticPage> {
  late final NisApiClient _api;
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _keyboardFocus = FocusNode();

  bool _loading = true;
  bool _started = false;
  bool _finished = false;
  String? _error;

  Map<String, dynamic>? _question;
  Map<String, dynamic>? _answerResult;

  int _questionsAsked = 0;
  int _topicsTested = 0;
  int _maxTopics = 15;
  int _correctCount = 0;
  String _mode = 'exam';

  bool _hasActiveSession = false;
  String _activeMode = '';
  int _activeQuestionsAsked = 0;
  int _activeTopicsTested = 0;
  int _activeMaxTopics = 0;

  late Stopwatch _stopwatch;
  Timer? _tickTimer;
  int _elapsedSeconds = 0;

  Map<String, dynamic>? _results;

  @override
  void initState() {
    super.initState();
    _api = context.read<NisApiClient>();
    _stopwatch = Stopwatch();
    _init();
  }

  @override
  void dispose() {
    _tickTimer?.cancel();
    _controller.dispose();
    _focusNode.dispose();
    _keyboardFocus.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      final status = await _api.getDiagnosticStatus();
      if (status['active'] == true && status['can_resume'] == true) {
        setState(() {
          _hasActiveSession = true;
          _activeMode = (status['mode'] as String?) ?? '';
          _activeQuestionsAsked = (status['questions_asked'] as int?) ?? 0;
          _activeTopicsTested = (status['topics_tested'] as int?) ?? 0;
          _activeMaxTopics = (status['max_topics'] as int?) ?? 15;
          _loading = false;
        });
        return;
      }
    } catch (e) {
      debugPrint('Diagnostic status check failed: $e');
    }

    setState(() => _loading = false);
  }

  Future<void> _resumeDiagnostic() async {
    setState(() { _loading = true; _error = null; _started = true; _finished = false;
      _hasActiveSession = false; _mode = _activeMode; });
    try {
      final q = await _api.getDiagnosticQuestion();
      _handleQuestion(q);
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось продолжить диагностику'; });
    }
  }

  Future<void> _cancelAndStartNew(String mode) async {
    setState(() { _loading = true; _hasActiveSession = false; });
    try {
      await _api.cancelDiagnostic();
    } catch (_) {}
    await _startDiagnostic(mode);
  }

  Future<bool> _onWillPop() async {
    if (!_started || _finished) return true;
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

  void _startQuestionTimer() {
    _stopwatch.reset(); _stopwatch.start(); _elapsedSeconds = 0;
    _tickTimer?.cancel();
    _tickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSeconds = _stopwatch.elapsed.inSeconds);
    });
  }

  void _stopQuestionTimer() {
    _stopwatch.stop(); _tickTimer?.cancel();
  }

  Future<void> _startDiagnostic(String mode) async {
    setState(() { _loading = true; _error = null; _started = true; _finished = false;
      _correctCount = 0; _results = null; _mode = mode; });
    try {
      final q = await _api.startDiagnostic(mode: mode);
      _handleQuestion(q);
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось начать диагностику'; });
    }
  }

  void _handleQuestion(Map<String, dynamic> q) {
    if (q['finished'] == true) { _finishDiagnostic(); return; }
    setState(() {
      _question = q; _answerResult = null; _loading = false;
      _questionsAsked = q['questions_asked'] ?? 0;
      _topicsTested = q['topics_tested'] ?? 0;
      _maxTopics = q['max_topics'] ?? 15;
      _controller.clear();
    });
    _startQuestionTimer();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focusNode.requestFocus();
    });
  }

  Future<void> _submitAnswer() async {
    final answer = _controller.text.trim();
    if (answer.isEmpty || _question == null) return;
    _stopQuestionTimer();
    setState(() => _loading = true);
    try {
      final result = await _api.submitDiagnosticAnswer(
        problemId: _question!['problem_id'],
        answer: answer,
        elapsedSec: _stopwatch.elapsedMilliseconds / 1000.0,
      );
      setState(() {
        _answerResult = result; _loading = false;
        _questionsAsked = result['questions_asked'] ?? _questionsAsked;
        _topicsTested = result['topics_tested'] ?? _topicsTested;
        if (result['is_correct'] == true) _correctCount++;
      });
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось отправить ответ'; });
    }
  }

  Future<void> _nextQuestion() async {
    setState(() => _loading = true);
    try {
      final q = await _api.getDiagnosticQuestion();
      _handleQuestion(q);
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось загрузить вопрос'; });
    }
  }

  Future<void> _finishDiagnostic() async {
    setState(() => _loading = true);
    try {
      final result = await _api.finishDiagnostic();
      setState(() { _finished = true; _results = result; _loading = false; });
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось завершить диагностику'; });
    }
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    if (_answerResult != null &&
        (event.logicalKey == LogicalKeyboardKey.arrowRight ||
         event.logicalKey == LogicalKeyboardKey.space)) {
      if (_answerResult!['has_next'] == true) _nextQuestion();
      else _finishDiagnostic();
    }
  }

  String _fmtTime(int s) => s < 60 ? '${s}с' : '${s ~/ 60}м ${s % 60}с';

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_started || _finished,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldLeave = await _onWillPop();
        if (shouldLeave && context.mounted) Navigator.of(context).pop();
      },
      child: KeyboardListener(
        focusNode: _keyboardFocus, autofocus: true, onKeyEvent: _handleKeyEvent,
        child: Scaffold(
          backgroundColor: const Color(0xFFFAF9F6),
          appBar: AppBar(
            backgroundColor: Colors.white, surfaceTintColor: Colors.white, elevation: 0.5,
            leading: BackButton(onPressed: () async {
              if (!_started || _finished) { Navigator.of(context).pop(); return; }
              final shouldLeave = await _onWillPop();
              if (shouldLeave && context.mounted) Navigator.of(context).pop();
            }),
            title: Row(children: [
              const Text('Диагностика',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              if (_started && !_finished) ...[
                const Spacer(),
                if (_answerResult == null && !_loading)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Text(_fmtTime(_elapsedSeconds),
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
                        color: _elapsedSeconds > 120 ? const Color(0xFFEF4444) : Colors.grey[400],
                        fontFeatures: const [FontFeature.tabularFigures()]))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(20)),
                  child: Text('${_topicsTested + 1}/$_maxTopics',
                    style: const TextStyle(color: Color(0xFF2563EB),
                      fontSize: 13, fontWeight: FontWeight.w600))),
              ],
            ])),
          body: _loading ? const Center(child: CircularProgressIndicator())
            : Align(alignment: Alignment.topCenter,
                child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: _buildContent()))),
        )),
    );
  }

  Widget _buildContent() {
    if (_error != null) return _buildError();
    if (_finished) return _buildResults();
    if (!_started && _hasActiveSession) return _buildResumePrompt();
    if (!_started) return _buildStart();
    if (_answerResult != null) return _buildAnswerResult();
    if (_question != null) return _buildQuestion();
    return const SizedBox.shrink();
  }

  Widget _buildResumePrompt() {
    final modeName = _activeMode == 'gaps' ? 'Проверка пробелов' : 'Подготовка к экзамену';
    return Column(children: [
      const SizedBox(height: 40),
      Container(
        width: 80, height: 80,
        decoration: BoxDecoration(
          color: const Color(0xFFFFA726),
          borderRadius: BorderRadius.circular(20)),
        child: const Icon(Icons.pause_circle_filled_rounded, color: Colors.white, size: 44)),
      const SizedBox(height: 24),
      const Text('Незавершённая диагностика',
        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
      const SizedBox(height: 12),
      Text('$modeName — $_activeTopicsTested из $_activeMaxTopics тем · $_activeQuestionsAsked вопросов',
        style: TextStyle(fontSize: 15, color: Colors.grey[600], height: 1.5),
        textAlign: TextAlign.center),
      const SizedBox(height: 8),
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: _activeMaxTopics > 0 ? _activeTopicsTested / _activeMaxTopics : 0,
          minHeight: 8,
          backgroundColor: const Color(0xFFE2E8F0),
          valueColor: const AlwaysStoppedAnimation(Color(0xFFFFA726)))),
      const SizedBox(height: 32),
      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: _resumeDiagnostic,
          icon: const Icon(Icons.play_arrow_rounded),
          label: const Text('Продолжить',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: FilledButton.styleFrom(
            minimumSize: const Size(0, 52),
            backgroundColor: const Color(0xFFFFA726)))),
      const SizedBox(height: 12),
      SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: () => setState(() => _hasActiveSession = false),
          icon: const Icon(Icons.restart_alt_rounded),
          label: const Text('Начать заново',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 52)))),
    ]);
  }

  Widget _buildStart() {
    return Column(children: [
      const SizedBox(height: 40),
      Container(
        width: 80, height: 80,
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF667EEA), Color(0xFF764BA2)]),
          borderRadius: BorderRadius.circular(20)),
        child: const Icon(Icons.psychology_rounded, color: Colors.white, size: 44)),
      const SizedBox(height: 24),
      const Text('Диагностика знаний',
        style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
      const SizedBox(height: 12),
      Text('15 тем — адаптивный алгоритм подберёт задачи под тебя.',
        style: TextStyle(fontSize: 15, color: Colors.grey[600], height: 1.5),
        textAlign: TextAlign.center),
      const SizedBox(height: 32),
      _ModeCard(
        title: 'Готовлюсь к экзамену', subtitle: '15 тем · 10-15 минут',
        description: 'Сложные темы первыми — проверь готовность',
        icon: Icons.school_rounded, color: const Color(0xFF2563EB),
        onStart: () => _cancelAndStartNew('exam')),
      const SizedBox(height: 12),
      _ModeCard(
        title: 'Проверяю пробелы', subtitle: '15 тем · 10-15 минут',
        description: 'С базовых тем вверх — найди слабые места',
        icon: Icons.search_rounded, color: const Color(0xFF7C3AED),
        onStart: () => _cancelAndStartNew('gaps')),
    ]);
  }

  Widget _buildQuestion() {
    final q = _question!;
    final text = q['text'] as String? ?? '';
    final nodeName = q['node_name'] as String?;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      // Progress bar
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: _maxTopics > 0 ? _topicsTested / _maxTopics : 0,
          minHeight: 6,
          backgroundColor: const Color(0xFFE2E8F0),
          valueColor: const AlwaysStoppedAnimation(Color(0xFF2563EB)))),
      const SizedBox(height: 4),
      Row(children: [
        Text('Тема ${_topicsTested + 1} из $_maxTopics',
          style: TextStyle(fontSize: 12, color: Colors.grey[500])),
        const Spacer(),
        Text('$_correctCount правильно',
          style: const TextStyle(fontSize: 12, color: Color(0xFF10B981), fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 16),

      // Problem card (shared widget)
      ProblemCard(
        text: text,
        nodeName: nodeName,
        counter: '${_questionsAsked + 1}'),
      const SizedBox(height: 16),

      // Answer input (shared widget)
      AnswerInput(
        controller: _controller,
        focusNode: _focusNode,
        onSubmit: _submitAnswer,
        onReport: () => showReportSheet(context, _api, q['problem_id']),
      ),
    ]);
  }

  Widget _buildAnswerResult() {
    final r = _answerResult!;
    final ok = r['is_correct'] == true;
    final hasNext = r['has_next'] == true;

    return Column(children: [
      // Progress
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          value: _maxTopics > 0 ? _topicsTested / _maxTopics : 0,
          minHeight: 6,
          backgroundColor: const Color(0xFFE2E8F0),
          valueColor: const AlwaysStoppedAnimation(Color(0xFF2563EB)))),
      const SizedBox(height: 16),

      // Result card (shared widget)
      ResultCard(
        isCorrect: ok,
        correctAnswer: r['correct_answer']?.toString(),
        solution: r['solution'] as String?,
        nodeName: _question?['node_name'] as String?,
        onReport: !ok ? () => showReportSheet(context, _api, _question!['problem_id']) : null,
      ),
      const SizedBox(height: 16),

      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: hasNext ? _nextQuestion : _finishDiagnostic,
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
            backgroundColor: const Color(0xFF2563EB)))),
      if (hasNext) ...[
        const SizedBox(height: 8),
        Text('→ или пробел', style: TextStyle(fontSize: 11, color: Colors.grey[400])),
      ],
    ]);
  }

  Widget _buildResults() {
    final r = _results ?? {};
    final mastered = (r['mastered_nodes'] as List?)?.length ?? 0;
    final failed = (r['failed_nodes'] as List?)?.length ?? 0;
    final summary = r['summary'] as String? ?? '';
    final masteredNodes = (r['mastered_nodes'] as List?) ?? [];
    final failedNodes = (r['failed_nodes'] as List?) ?? [];

    return Column(children: [
      const SizedBox(height: 20),
      Container(
        width: 80, height: 80,
        decoration: BoxDecoration(
          color: const Color(0xFF10B981),
          borderRadius: BorderRadius.circular(20)),
        child: const Icon(Icons.check_rounded, color: Colors.white, size: 44)),
      const SizedBox(height: 24),
      const Text('Диагностика завершена!',
        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
      const SizedBox(height: 8),
      Text(summary, style: TextStyle(fontSize: 14, color: Colors.grey[600]),
        textAlign: TextAlign.center),
      const SizedBox(height: 24),

      Row(children: [
        _ResultStat(label: 'Освоено', value: '$mastered', color: const Color(0xFF10B981)),
        const SizedBox(width: 10),
        _ResultStat(label: 'Пробелы', value: '$failed', color: const Color(0xFFEF4444)),
        const SizedBox(width: 10),
        _ResultStat(label: 'Правильно', value: '$_correctCount',  color: const Color(0xFF2563EB)),
      ]),
      const SizedBox(height: 20),

      // Mastered topics
      if (masteredNodes.isNotEmpty)
        _TopicList(title: '✅ Освоенные темы', topics: masteredNodes, color: const Color(0xFF10B981)),
      if (failedNodes.isNotEmpty)
        _TopicList(title: '❌ Слабые темы', topics: failedNodes, color: const Color(0xFFEF4444)),

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
            backgroundColor: const Color(0xFF2563EB)))),
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
      FilledButton(onPressed: () => setState(() { _error = null; _started = false; }),
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
      width: double.infinity, padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))]),
      child: Row(children: [
        Container(width: 48, height: 48,
          decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
          child: Icon(icon, color: color, size: 26)),
        const SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
          Text(subtitle, style: TextStyle(fontSize: 12, color: Colors.grey[500])),
          const SizedBox(height: 2),
          Text(description, style: TextStyle(fontSize: 12, color: Colors.grey[400])),
        ])),
        FilledButton(onPressed: onStart,
          style: FilledButton.styleFrom(backgroundColor: color, padding: const EdgeInsets.symmetric(horizontal: 16)),
          child: const Text('Начать')),
      ]));
  }
}

class _ResultStat extends StatelessWidget {
  const _ResultStat({required this.label, required this.value, required this.color});
  final String label, value;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Expanded(child: Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(14)),
      child: Column(children: [
        Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
      ])));
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
