import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:kodi_core/kodi_core.dart';

// ── Events ────────────────────────────────────────────────────
abstract class DiagnosticEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class DiagnosticCheckSession extends DiagnosticEvent {}

class DiagnosticResumeRequested extends DiagnosticEvent {}

class DiagnosticStartRequested extends DiagnosticEvent {
  DiagnosticStartRequested(this.mode);
  final String mode;
  @override
  List<Object?> get props => [mode];
}

class DiagnosticCancelAndStartNew extends DiagnosticEvent {
  DiagnosticCancelAndStartNew(this.mode);
  final String mode;
  @override
  List<Object?> get props => [mode];
}

class DiagnosticAnswerSubmitted extends DiagnosticEvent {
  DiagnosticAnswerSubmitted(this.answer);
  final String answer;
  @override
  List<Object?> get props => [answer];
}

class DiagnosticNextQuestionRequested extends DiagnosticEvent {}

class DiagnosticFinishRequested extends DiagnosticEvent {}

class DiagnosticDismissResumePrompt extends DiagnosticEvent {}

class DiagnosticErrorDismissed extends DiagnosticEvent {}

class _DiagnosticTimerTicked extends DiagnosticEvent {}

// ── States ────────────────────────────────────────────────────
abstract class DiagnosticState extends Equatable {
  @override
  List<Object?> get props => [];
}

class DiagnosticInitial extends DiagnosticState {}

class DiagnosticLoading extends DiagnosticState {}

class DiagnosticActiveSessionFound extends DiagnosticState {
  DiagnosticActiveSessionFound({
    required this.activeMode,
    required this.activeQuestionsAsked,
    required this.activeTopicsTested,
    required this.activeMaxTopics,
  });
  final String activeMode;
  final int activeQuestionsAsked;
  final int activeTopicsTested;
  final int activeMaxTopics;
  @override
  List<Object?> get props =>
      [activeMode, activeQuestionsAsked, activeTopicsTested, activeMaxTopics];
}

class DiagnosticModeSelection extends DiagnosticState {}

class DiagnosticQuestionReady extends DiagnosticState {
  DiagnosticQuestionReady({
    required this.question,
    required this.questionsAsked,
    required this.topicsTested,
    required this.maxTopics,
    required this.correctCount,
    required this.mode,
    required this.elapsedSeconds,
  });
  final Map<String, dynamic> question;
  final int questionsAsked;
  final int topicsTested;
  final int maxTopics;
  final int correctCount;
  final String mode;
  final int elapsedSeconds;
  @override
  List<Object?> get props =>
      [questionsAsked, topicsTested, maxTopics, correctCount, mode, elapsedSeconds];
}

class DiagnosticAnswerShown extends DiagnosticState {
  DiagnosticAnswerShown({
    required this.question,
    required this.answerResult,
    required this.questionsAsked,
    required this.topicsTested,
    required this.maxTopics,
    required this.correctCount,
    required this.mode,
  });
  final Map<String, dynamic> question;
  final Map<String, dynamic> answerResult;
  final int questionsAsked;
  final int topicsTested;
  final int maxTopics;
  final int correctCount;
  final String mode;
  @override
  List<Object?> get props =>
      [questionsAsked, topicsTested, maxTopics, correctCount, mode];
}

class DiagnosticFinished extends DiagnosticState {
  DiagnosticFinished({required this.results, required this.correctCount});
  final Map<String, dynamic> results;
  final int correctCount;
  @override
  List<Object?> get props => [correctCount];
}

class DiagnosticError extends DiagnosticState {
  DiagnosticError(this.message, {this.wasStarted = false});
  final String message;
  final bool wasStarted;
  @override
  List<Object?> get props => [message, wasStarted];
}

// ── Bloc ──────────────────────────────────────────────────────
class DiagnosticBloc extends Bloc<DiagnosticEvent, DiagnosticState> {
  DiagnosticBloc({required this.api}) : super(DiagnosticInitial()) {
    on<DiagnosticCheckSession>(_onCheckSession);
    on<DiagnosticResumeRequested>(_onResume);
    on<DiagnosticStartRequested>(_onStart);
    on<DiagnosticCancelAndStartNew>(_onCancelAndStart);
    on<DiagnosticAnswerSubmitted>(_onAnswerSubmitted);
    on<DiagnosticNextQuestionRequested>(_onNextQuestion);
    on<DiagnosticFinishRequested>(_onFinish);
    on<DiagnosticDismissResumePrompt>(_onDismissResume);
    on<DiagnosticErrorDismissed>(_onErrorDismissed);
    on<_DiagnosticTimerTicked>(_onTimerTicked);
  }

  final NisApiClient api;

  String _mode = 'exam';
  int _questionsAsked = 0;
  int _topicsTested = 0;
  int _maxTopics = 15;
  int _correctCount = 0;
  Map<String, dynamic>? _currentQuestion;

  final Stopwatch _stopwatch = Stopwatch();
  StreamSubscription<void>? _timerSub;

  // ── Event handlers ─────────────────────────────────────────

  Future<void> _onCheckSession(
    DiagnosticCheckSession event,
    Emitter<DiagnosticState> emit,
  ) async {
    emit(DiagnosticLoading());
    try {
      final status = await api.getDiagnosticStatus();
      if (status['active'] == true && status['can_resume'] == true) {
        emit(DiagnosticActiveSessionFound(
          activeMode: (status['mode'] as String?) ?? '',
          activeQuestionsAsked: (status['questions_asked'] as int?) ?? 0,
          activeTopicsTested: (status['topics_tested'] as int?) ?? 0,
          activeMaxTopics: (status['max_topics'] as int?) ?? 15,
        ));
        return;
      }
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onCheckSession] $e\n$st');
      // Status check failed — just show mode selection
    }
    emit(DiagnosticModeSelection());
  }

  Future<void> _onResume(
    DiagnosticResumeRequested event,
    Emitter<DiagnosticState> emit,
  ) async {
    final s = state;
    if (s is DiagnosticActiveSessionFound) {
      _mode = s.activeMode;
    }
    emit(DiagnosticLoading());
    try {
      final q = await api.getDiagnosticQuestion();
      _handleQuestion(q, emit);
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onResume] $e\n$st');
      emit(DiagnosticError('Не удалось продолжить диагностику', wasStarted: true));
    }
  }

  Future<void> _onStart(
    DiagnosticStartRequested event,
    Emitter<DiagnosticState> emit,
  ) async {
    _mode = event.mode;
    _correctCount = 0;
    emit(DiagnosticLoading());
    try {
      final q = await api.startDiagnostic(mode: event.mode);
      _handleQuestion(q, emit);
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onStart] $e\n$st');
      emit(DiagnosticError('Не удалось начать диагностику', wasStarted: true));
    }
  }

  Future<void> _onCancelAndStart(
    DiagnosticCancelAndStartNew event,
    Emitter<DiagnosticState> emit,
  ) async {
    emit(DiagnosticLoading());
    try {
      await api.cancelDiagnostic();
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onCancelAndStart] cancel $e\n$st');
      // cancel is best-effort
    }
    _mode = event.mode;
    _correctCount = 0;
    try {
      final q = await api.startDiagnostic(mode: event.mode);
      _handleQuestion(q, emit);
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onCancelAndStart] start $e\n$st');
      emit(DiagnosticError('Не удалось начать диагностику', wasStarted: true));
    }
  }

  Future<void> _onAnswerSubmitted(
    DiagnosticAnswerSubmitted event,
    Emitter<DiagnosticState> emit,
  ) async {
    if (event.answer.isEmpty || _currentQuestion == null) return;
    _stopTimer();
    emit(DiagnosticLoading());
    try {
      final result = await api.submitDiagnosticAnswer(
        problemId: _currentQuestion!['problem_id'],
        answer: event.answer,
        elapsedSec: _stopwatch.elapsedMilliseconds / 1000.0,
      );
      _questionsAsked = result['questions_asked'] ?? _questionsAsked;
      _topicsTested = result['topics_tested'] ?? _topicsTested;
      if (result['is_correct'] == true) _correctCount++;
      emit(DiagnosticAnswerShown(
        question: _currentQuestion!,
        answerResult: result,
        questionsAsked: _questionsAsked,
        topicsTested: _topicsTested,
        maxTopics: _maxTopics,
        correctCount: _correctCount,
        mode: _mode,
      ));
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onAnswerSubmitted] $e\n$st');
      emit(DiagnosticError('Не удалось отправить ответ', wasStarted: true));
    }
  }

  Future<void> _onNextQuestion(
    DiagnosticNextQuestionRequested event,
    Emitter<DiagnosticState> emit,
  ) async {
    emit(DiagnosticLoading());
    try {
      final q = await api.getDiagnosticQuestion();
      _handleQuestion(q, emit);
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onNextQuestion] $e\n$st');
      emit(DiagnosticError('Не удалось загрузить вопрос', wasStarted: true));
    }
  }

  Future<void> _onFinish(
    DiagnosticFinishRequested event,
    Emitter<DiagnosticState> emit,
  ) async {
    _stopTimer();
    emit(DiagnosticLoading());
    try {
      final result = await api.finishDiagnostic();
      emit(DiagnosticFinished(results: result, correctCount: _correctCount));
    } on NetworkException catch (e) {
      emit(DiagnosticError(e.message, wasStarted: true));
    } on ApiException catch (e) {
      emit(DiagnosticError(e.userMessage, wasStarted: true));
    } catch (e, st) {
      debugPrint('[DiagnosticBloc._onFinish] $e\n$st');
      emit(DiagnosticError('Не удалось завершить диагностику', wasStarted: true));
    }
  }

  void _onDismissResume(
    DiagnosticDismissResumePrompt event,
    Emitter<DiagnosticState> emit,
  ) {
    emit(DiagnosticModeSelection());
  }

  void _onErrorDismissed(
    DiagnosticErrorDismissed event,
    Emitter<DiagnosticState> emit,
  ) {
    emit(DiagnosticModeSelection());
  }

  void _onTimerTicked(
    _DiagnosticTimerTicked event,
    Emitter<DiagnosticState> emit,
  ) {
    final s = state;
    if (s is DiagnosticQuestionReady) {
      emit(DiagnosticQuestionReady(
        question: s.question,
        questionsAsked: s.questionsAsked,
        topicsTested: s.topicsTested,
        maxTopics: s.maxTopics,
        correctCount: s.correctCount,
        mode: s.mode,
        elapsedSeconds: _stopwatch.elapsed.inSeconds,
      ));
    }
  }

  // ── Helpers ────────────────────────────────────────────────

  void _handleQuestion(Map<String, dynamic> q, Emitter<DiagnosticState> emit) {
    if (q['finished'] == true) {
      _onFinish(DiagnosticFinishRequested(), emit);
      return;
    }
    _currentQuestion = q;
    _questionsAsked = q['questions_asked'] ?? 0;
    _topicsTested = q['topics_tested'] ?? 0;
    _maxTopics = q['max_topics'] ?? 15;
    _startTimer();
    emit(DiagnosticQuestionReady(
      question: q,
      questionsAsked: _questionsAsked,
      topicsTested: _topicsTested,
      maxTopics: _maxTopics,
      correctCount: _correctCount,
      mode: _mode,
      elapsedSeconds: 0,
    ));
  }

  void _startTimer() {
    _stopwatch.reset();
    _stopwatch.start();
    _timerSub?.cancel();
    _timerSub = Stream.periodic(const Duration(seconds: 1))
        .listen((_) => add(_DiagnosticTimerTicked()));
  }

  void _stopTimer() {
    _stopwatch.stop();
    _timerSub?.cancel();
  }

  @override
  Future<void> close() {
    _timerSub?.cancel();
    _stopwatch.stop();
    return super.close();
  }
}
