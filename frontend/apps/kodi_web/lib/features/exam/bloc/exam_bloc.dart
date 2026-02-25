import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:kodi_core/kodi_core.dart';

// ── Events ────────────────────────────────────────────────────
abstract class ExamEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class ExamStartRequested extends ExamEvent {
  ExamStartRequested({required this.numProblems, required this.timeMinutes});
  final int numProblems;
  final int timeMinutes;
  @override
  List<Object?> get props => [numProblems, timeMinutes];
}

class ExamAnswerSubmitted extends ExamEvent {
  ExamAnswerSubmitted(this.answer);
  final String answer;
  @override
  List<Object?> get props => [answer];
}

class ExamProblemSkipped extends ExamEvent {}

class ExamNextProblemRequested extends ExamEvent {}

class ExamFinishRequested extends ExamEvent {}

class _ExamTimerTicked extends ExamEvent {}

class ExamResetRequested extends ExamEvent {}

// ── States ────────────────────────────────────────────────────
abstract class ExamState extends Equatable {
  @override
  List<Object?> get props => [];
}

class ExamInitial extends ExamState {}

class ExamLoading extends ExamState {}

class ExamQuestionReady extends ExamState {
  ExamQuestionReady({
    required this.problems,
    required this.currentIndex,
    required this.correct,
    required this.answered,
    required this.secondsLeft,
    required this.timeMinutes,
    required this.results,
  });
  final List<Map<String, dynamic>> problems;
  final int currentIndex;
  final int correct;
  final int answered;
  final int secondsLeft;
  final int timeMinutes;
  final Map<int, bool> results;
  @override
  List<Object?> get props =>
      [currentIndex, correct, answered, secondsLeft];
}

class ExamAnswerShown extends ExamState {
  ExamAnswerShown({
    required this.problems,
    required this.currentIndex,
    required this.answerResult,
    required this.correct,
    required this.answered,
    required this.secondsLeft,
    required this.timeMinutes,
    required this.results,
  });
  final List<Map<String, dynamic>> problems;
  final int currentIndex;
  final Map<String, dynamic> answerResult;
  final int correct;
  final int answered;
  final int secondsLeft;
  final int timeMinutes;
  final Map<int, bool> results;
  @override
  List<Object?> get props =>
      [currentIndex, correct, answered, secondsLeft];
}

class ExamFinished extends ExamState {
  ExamFinished({
    required this.correct,
    required this.answered,
    required this.totalProblems,
    required this.timeUsedSeconds,
    required this.timeMinutes,
  });
  final int correct;
  final int answered;
  final int totalProblems;
  final int timeUsedSeconds;
  final int timeMinutes;
  @override
  List<Object?> get props =>
      [correct, answered, totalProblems, timeUsedSeconds];
}

class ExamError extends ExamState {
  ExamError(this.message);
  final String message;
  @override
  List<Object?> get props => [message];
}

// ── Bloc ──────────────────────────────────────────────────────
class ExamBloc extends Bloc<ExamEvent, ExamState> {
  ExamBloc({required this.api}) : super(ExamInitial()) {
    on<ExamStartRequested>(_onStart);
    on<ExamAnswerSubmitted>(_onAnswerSubmitted);
    on<ExamProblemSkipped>(_onSkip);
    on<ExamNextProblemRequested>(_onNext);
    on<ExamFinishRequested>(_onFinish);
    on<_ExamTimerTicked>(_onTimerTicked);
    on<ExamResetRequested>(_onReset);
  }

  final NisApiClient api;

  List<Map<String, dynamic>> _problems = [];
  int _currentIndex = 0;
  int _correct = 0;
  int _answered = 0;
  int _secondsLeft = 0;
  int _timeMinutes = 0;
  final Map<int, bool> _results = {};

  StreamSubscription<void>? _timerSub;

  Future<void> _onStart(
    ExamStartRequested event,
    Emitter<ExamState> emit,
  ) async {
    _timeMinutes = event.timeMinutes;
    emit(ExamLoading());
    try {
      final resp = await api.post('/api/practice/exam/start?lang=${api.lang}', {
        'num_problems': event.numProblems,
        'time_minutes': event.timeMinutes,
      });
      final problems = (resp['problems'] as List).cast<Map<String, dynamic>>();
      _problems = problems;
      _currentIndex = 0;
      _correct = 0;
      _answered = 0;
      _results.clear();
      _secondsLeft = event.timeMinutes * 60;
      _startTimer();
      emit(_questionState());
    } on NetworkException catch (e) {
      emit(ExamError(e.message));
    } on ApiException catch (e) {
      emit(ExamError(e.userMessage));
    } catch (e, st) {
      debugPrint('[ExamBloc._onStart] $e\n$st');
      emit(ExamError('examStartError'));
    }
  }

  Future<void> _onAnswerSubmitted(
    ExamAnswerSubmitted event,
    Emitter<ExamState> emit,
  ) async {
    if (event.answer.isEmpty || _currentIndex >= _problems.length) return;
    final problem = _problems[_currentIndex];
    emit(ExamLoading());
    try {
      final result = await api.post('/api/practice/answer', {
        'problem_id': problem['problem_id'],
        'answer': event.answer,
      });
      final isCorrect = result['is_correct'] == true;
      _results[problem['problem_id']] = isCorrect;
      if (isCorrect) _correct++;
      _answered++;
      emit(ExamAnswerShown(
        problems: _problems,
        currentIndex: _currentIndex,
        answerResult: result,
        correct: _correct,
        answered: _answered,
        secondsLeft: _secondsLeft,
        timeMinutes: _timeMinutes,
        results: Map.of(_results),
      ));
    } on NetworkException catch (e) {
      emit(ExamError(e.message));
    } on ApiException catch (e) {
      emit(ExamError(e.userMessage));
    } catch (e, st) {
      debugPrint('[ExamBloc._onAnswerSubmitted] $e\n$st');
      emit(ExamError('examAnswerError'));
    }
  }

  void _onSkip(
    ExamProblemSkipped event,
    Emitter<ExamState> emit,
  ) {
    _answered++;
    _results[_problems[_currentIndex]['problem_id']] = false;
    _advanceOrFinish(emit);
  }

  void _onNext(
    ExamNextProblemRequested event,
    Emitter<ExamState> emit,
  ) {
    _advanceOrFinish(emit);
  }

  void _onFinish(
    ExamFinishRequested event,
    Emitter<ExamState> emit,
  ) {
    _finishExam(emit);
  }

  void _onTimerTicked(
    _ExamTimerTicked event,
    Emitter<ExamState> emit,
  ) {
    _secondsLeft--;
    if (_secondsLeft <= 0) {
      _finishExam(emit);
      return;
    }
    final s = state;
    if (s is ExamQuestionReady) {
      emit(ExamQuestionReady(
        problems: s.problems,
        currentIndex: s.currentIndex,
        correct: s.correct,
        answered: s.answered,
        secondsLeft: _secondsLeft,
        timeMinutes: s.timeMinutes,
        results: s.results,
      ));
    } else if (s is ExamAnswerShown) {
      emit(ExamAnswerShown(
        problems: s.problems,
        currentIndex: s.currentIndex,
        answerResult: s.answerResult,
        correct: s.correct,
        answered: s.answered,
        secondsLeft: _secondsLeft,
        timeMinutes: s.timeMinutes,
        results: s.results,
      ));
    }
  }

  void _onReset(
    ExamResetRequested event,
    Emitter<ExamState> emit,
  ) {
    _timerSub?.cancel();
    _problems.clear();
    _results.clear();
    emit(ExamInitial());
  }

  // ── Helpers ────────────────────────────────────────────────

  void _advanceOrFinish(Emitter<ExamState> emit) {
    if (_currentIndex + 1 >= _problems.length) {
      _finishExam(emit);
    } else {
      _currentIndex++;
      emit(_questionState());
    }
  }

  void _finishExam(Emitter<ExamState> emit) {
    _timerSub?.cancel();
    emit(ExamFinished(
      correct: _correct,
      answered: _answered,
      totalProblems: _problems.length,
      timeUsedSeconds: _timeMinutes * 60 - _secondsLeft,
      timeMinutes: _timeMinutes,
    ));
  }

  ExamQuestionReady _questionState() => ExamQuestionReady(
        problems: _problems,
        currentIndex: _currentIndex,
        correct: _correct,
        answered: _answered,
        secondsLeft: _secondsLeft,
        timeMinutes: _timeMinutes,
        results: Map.of(_results),
      );

  void _startTimer() {
    _timerSub?.cancel();
    _timerSub = Stream.periodic(const Duration(seconds: 1))
        .listen((_) => add(_ExamTimerTicked()));
  }

  @override
  Future<void> close() {
    _timerSub?.cancel();
    return super.close();
  }
}
