import 'package:equatable/equatable.dart';

class Stats extends Equatable {
  const Stats({
    required this.solved,
    required this.correct,
    required this.accuracy,
    required this.avgTimeS,
    required this.masteredCount,
    required this.totalNodes,
    this.currentStreak = 0,
    this.longestStreak = 0,
  });

  final int solved;
  final int correct;
  final int accuracy;
  final double avgTimeS;
  final int masteredCount;
  final int totalNodes;
  final int currentStreak;
  final int longestStreak;

  factory Stats.fromJson(Map<String, dynamic> json) => Stats(
        solved: json['solved'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        accuracy: json['accuracy'] as int? ?? 0,
        avgTimeS: (json['avg_time_s'] as num?)?.toDouble() ?? 0.0,
        masteredCount: json['mastered_count'] as int? ?? 0,
        totalNodes: json['total_nodes'] as int? ?? 0,
        currentStreak: json['current_streak'] as int? ?? 0,
        longestStreak: json['longest_streak'] as int? ?? 0,
      );

  double get masteryPercent =>
      totalNodes > 0 ? masteredCount / totalNodes : 0.0;

  @override
  List<Object?> get props =>
      [solved, correct, accuracy, avgTimeS, masteredCount, totalNodes, currentStreak, longestStreak];
}
