import 'package:equatable/equatable.dart';

class Problem extends Equatable {
  const Problem({
    required this.problemId,
    required this.nodeId,
    required this.nodeName,
    required this.text,
    this.imagePath,
    this.answerType,
    this.difficulty,
    this.subDifficulty,
    required this.count,
  });

  final int problemId;
  final String nodeId;
  final String nodeName;
  final String text;
  final String? imagePath;
  final String? answerType;
  final int? difficulty;
  final int? subDifficulty;
  final int count;

  factory Problem.fromJson(Map<String, dynamic> json) => Problem(
        problemId: json['problem_id'] as int,
        nodeId: json['node_id'] as String,
        nodeName: json['node_name'] as String,
        text: json['text'] as String,
        imagePath: json['image_path'] as String?,
        answerType: json['answer_type'] as String?,
        difficulty: json['difficulty'] as int?,
        subDifficulty: json['sub_difficulty'] as int?,
        count: json['count'] as int? ?? 1,
      );

  @override
  List<Object?> get props => [problemId, nodeId];
}

class AnswerResult extends Equatable {
  const AnswerResult({
    required this.isCorrect,
    required this.correctAnswer,
    this.solution,
    required this.pMastery,
    required this.isMastered,
    this.llmNote,
  });

  final bool isCorrect;
  final String correctAnswer;
  final String? solution;
  final double pMastery;
  final bool isMastered;
  final String? llmNote;

  factory AnswerResult.fromJson(Map<String, dynamic> json) => AnswerResult(
        isCorrect: json['is_correct'] as bool,
        correctAnswer: json['correct_answer'] as String,
        solution: json['solution'] as String?,
        pMastery: (json['p_mastery'] as num).toDouble(),
        isMastered: json['is_mastered'] as bool,
        llmNote: json['llm_note'] as String?,
      );

  @override
  List<Object?> get props => [isCorrect, pMastery];
}
