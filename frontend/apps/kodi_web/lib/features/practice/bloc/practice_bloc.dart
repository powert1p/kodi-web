import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:kodi_core/kodi_core.dart';

// ── Events ────────────────────────────────────────────────────
abstract class PracticeEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class PracticeStarted extends PracticeEvent {
  PracticeStarted({this.tag, this.nodeId});
  final String? tag;
  final String? nodeId;
  @override
  List<Object?> get props => [tag, nodeId];
}

class PracticeAnswerSubmitted extends PracticeEvent {
  PracticeAnswerSubmitted(this.answer);
  final String answer;
  @override
  List<Object?> get props => [answer];
}

class PracticeProblemSkipped extends PracticeEvent {}

class PracticeNextRequested extends PracticeEvent {}

class _PracticeTimerTicked extends PracticeEvent {}

// ── States ────────────────────────────────────────────────────
abstract class PracticeState extends Equatable {
  @override
  List<Object?> get props => [];
}

class PracticeInitial extends PracticeState {}

class PracticeLoading extends PracticeState {}

class PracticeProblemReady extends PracticeState {
  PracticeProblemReady({
    required this.problem,
    required this.count,
    required this.correct,
    required this.combo,
    required this.bestCombo,
    required this.elapsedSeconds,
    required this.totalTimeSpent,
  });

  final Problem problem;
  final int count;
  final int correct;
  final int combo;
  final int bestCombo;
  final int elapsedSeconds;
  final double totalTimeSpent;

  @override
  List<Object?> get props =>
      [problem, count, correct, combo, bestCombo, elapsedSeconds];
}

class PracticeAnswerShown extends PracticeState {
  PracticeAnswerShown({
    required this.problem,
    required this.result,
    required this.count,
    required this.correct,
    required this.combo,
    required this.bestCombo,
    required this.totalTimeSpent,
  });

  final Problem problem;
  final AnswerResult result;
  final int count;
  final int correct;
  final int combo;
  final int bestCombo;
  final double totalTimeSpent;

  @override
  List<Object?> get props =>
      [problem, result, count, correct, combo, bestCombo];
}

class PracticeAllDone extends PracticeState {}

class PracticeError extends PracticeState {
  PracticeError(this.message);
  final String message;
  @override
  List<Object?> get props => [message];
}

// ── Bloc ──────────────────────────────────────────────────────
class PracticeBloc extends Bloc<PracticeEvent, PracticeState> {
  PracticeBloc({required this.api}) : super(PracticeInitial()) {
    on<PracticeStarted>(_onStarted);
    on<PracticeAnswerSubmitted>(_onAnswerSubmitted);
    on<PracticeProblemSkipped>(_onProblemSkipped);
    on<PracticeNextRequested>(_onNextRequested);
    on<_PracticeTimerTicked>(_onTimerTicked);
  }

  final NisApiClient api;

  String? _tag;
  String? _nodeId;
  int _count = 1;
  int _correct = 0;
  int _combo = 0;
  int _bestCombo = 0;
  double _totalTimeSpent = 0;
  Problem? _currentProblem;

  final Stopwatch _stopwatch = Stopwatch();
  StreamSubscription<void>? _timerSub;

  Future<void> _onStarted(
    PracticeStarted event,
    Emitter<PracticeState> emit,
  ) async {
    _tag = event.tag;
    _nodeId = event.nodeId;
    await _loadNext(emit);
  }

  Future<void> _onAnswerSubmitted(
    PracticeAnswerSubmitted event,
    Emitter<PracticeState> emit,
  ) async {
    if (_currentProblem == null || event.answer.isEmpty) return;
    _stopTimer();
    emit(PracticeLoading());
    try {
      final result = await api.submitAnswer(_currentProblem!.problemId, event.answer);
      _count++;
      if (result.isCorrect) {
        _correct++;
        _combo++;
        if (_combo > _bestCombo) _bestCombo = _combo;
      } else {
        _combo = 0;
      }
      emit(PracticeAnswerShown(
        problem: _currentProblem!,
        result: result,
        count: _count,
        correct: _correct,
        combo: _combo,
        bestCombo: _bestCombo,
        totalTimeSpent: _totalTimeSpent,
      ));
    } on NetworkException catch (e) {
      emit(PracticeError(e.message));
    } on ApiException catch (e) {
      emit(PracticeError(e.userMessage));
    } catch (e, st) {
      debugPrint('[PracticeBloc._onAnswerSubmitted] $e\n$st');
      emit(PracticeError('Не удалось отправить ответ'));
    }
  }

  Future<void> _onProblemSkipped(
    PracticeProblemSkipped event,
    Emitter<PracticeState> emit,
  ) async {
    if (_currentProblem == null) return;
    _stopTimer();
    _combo = 0;
    try {
      await api.skipProblem(_currentProblem!.problemId);
    } catch (e, st) {
      debugPrint('[PracticeBloc._onProblemSkipped] $e\n$st');
      // skip is best-effort
    }
    _count++;
    await _loadNext(emit);
  }

  Future<void> _onNextRequested(
    PracticeNextRequested event,
    Emitter<PracticeState> emit,
  ) async {
    await _loadNext(emit);
  }

  void _onTimerTicked(
    _PracticeTimerTicked event,
    Emitter<PracticeState> emit,
  ) {
    final s = state;
    if (s is PracticeProblemReady) {
      emit(PracticeProblemReady(
        problem: s.problem,
        count: s.count,
        correct: s.correct,
        combo: s.combo,
        bestCombo: s.bestCombo,
        elapsedSeconds: _stopwatch.elapsed.inSeconds,
        totalTimeSpent: s.totalTimeSpent,
      ));
    }
  }

  Future<void> _loadNext(Emitter<PracticeState> emit) async {
    emit(PracticeLoading());
    try {
      final problem = await api.getNextProblem(
        count: _count,
        tag: _tag,
        nodeId: _nodeId,
      );
      _currentProblem = problem;
      _startTimer();
      emit(PracticeProblemReady(
        problem: problem,
        count: _count,
        correct: _correct,
        combo: _combo,
        bestCombo: _bestCombo,
        elapsedSeconds: 0,
        totalTimeSpent: _totalTimeSpent,
      ));
    } on NetworkException catch (e) {
      emit(PracticeError(e.message));
    } on ApiException catch (e) {
      emit(PracticeError(e.userMessage));
    } catch (e, st) {
      debugPrint('[PracticeBloc._loadNext] $e\n$st');
      emit(PracticeError('Не удалось загрузить задачу'));
    }
  }

  void _startTimer() {
    _stopwatch.reset();
    _stopwatch.start();
    _timerSub?.cancel();
    _timerSub = Stream.periodic(const Duration(seconds: 1))
        .listen((_) => add(_PracticeTimerTicked()));
  }

  void _stopTimer() {
    _stopwatch.stop();
    _timerSub?.cancel();
    _totalTimeSpent += _stopwatch.elapsed.inMilliseconds / 1000.0;
  }

  @override
  Future<void> close() {
    _timerSub?.cancel();
    _stopwatch.stop();
    return super.close();
  }
}
