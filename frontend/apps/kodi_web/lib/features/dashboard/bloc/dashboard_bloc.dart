import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:kodi_core/kodi_core.dart';

// ── Events ────────────────────────────────────────────────────
abstract class DashboardEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class DashboardLoad extends DashboardEvent {}

// ── States ────────────────────────────────────────────────────
abstract class DashboardState extends Equatable {
  @override
  List<Object?> get props => [];
}

class DashboardInitial extends DashboardState {}

class DashboardLoading extends DashboardState {}

class DashboardLoaded extends DashboardState {
  DashboardLoaded({
    required this.student,
    required this.stats,
    required this.nodes,
    required this.leaderboard,
  }) : loadedAt = DateTime.now();

  final Student student;
  final Stats stats;
  final List<GraphNode> nodes;
  final List<LeaderboardEntry> leaderboard;
  final DateTime loadedAt;

  @override
  List<Object?> get props => [student, stats, nodes, leaderboard, loadedAt];
}

class DashboardError extends DashboardState {
  DashboardError(this.message);
  final String message;
  @override
  List<Object?> get props => [message];
}

// ── LeaderboardEntry ──────────────────────────────────────────
class LeaderboardEntry extends Equatable {
  const LeaderboardEntry({
    required this.name,
    required this.solved,
    required this.correct,
    required this.accuracy,
    required this.mastered,
    required this.isCurrent,
  });

  final String name;
  final int solved;
  final int correct;
  final int accuracy;
  final int mastered;
  final bool isCurrent;

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) =>
      LeaderboardEntry(
        name: json['name'] as String? ?? 'Ученик',
        solved: json['solved'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        accuracy: json['accuracy'] as int? ?? 0,
        mastered: json['mastered'] as int? ?? 0,
        isCurrent: json['is_current'] as bool? ?? false,
      );

  @override
  List<Object?> get props => [name, solved, isCurrent];
}

// ── Bloc ──────────────────────────────────────────────────────
class DashboardBloc extends Bloc<DashboardEvent, DashboardState> {
  DashboardBloc({required this.api}) : super(DashboardInitial()) {
    on<DashboardLoad>(_onLoad);
  }

  final NisApiClient api;

  Future<void> _onLoad(
    DashboardLoad event,
    Emitter<DashboardState> emit,
  ) async {
    emit(DashboardLoading());
    try {
      // Parallel fetch: me + stats come from separate endpoints,
      // graph data has nodes + leaderboard
      final results = await Future.wait([
        api.getMe(),
        api.getStats(),
        api.getGraphData(),
      ]);

      final student = results[0] as Student;
      final stats = results[1] as Stats;
      final graphData = results[2] as Map<String, dynamic>;

      final nodes = (graphData['nodes'] as List<dynamic>)
          .map((n) => GraphNode.fromJson(n as Map<String, dynamic>))
          .toList();

      final leaderboard = (graphData['leaderboard'] as List<dynamic>?)
              ?.map(
                  (e) => LeaderboardEntry.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];

      emit(DashboardLoaded(
        student: student,
        stats: stats,
        nodes: nodes,
        leaderboard: leaderboard,
      ));
    } on NetworkException catch (e) {
      emit(DashboardError(e.message));
    } on ApiException catch (e) {
      emit(DashboardError(e.userMessage));
    } catch (_) {
      emit(DashboardError('Не удалось загрузить данные'));
    }
  }
}
