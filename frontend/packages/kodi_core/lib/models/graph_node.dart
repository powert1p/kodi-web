import 'package:equatable/equatable.dart';

class GraphNode extends Equatable {
  const GraphNode({
    required this.id,
    required this.nameRu,
    required this.nameKz,
    required this.tag,
    required this.zone,
    required this.status,
    this.pMastery,
    required this.isFringe,
    required this.isBlocked,
    required this.difficulty,
    required this.downstream,
    this.qTotal = 0,
    this.qCorrect = 0,
  });

  final String id;
  final String nameRu;
  final String nameKz;
  final String tag;
  final int zone;
  final String status; // mastered | partial | failed | untested
  final double? pMastery;
  final bool isFringe;
  final bool isBlocked;
  final int difficulty;
  final int downstream;
  final int qTotal;
  final int qCorrect;

  String name(String lang) => lang == 'kz' ? nameKz : nameRu;

  factory GraphNode.fromJson(Map<String, dynamic> json) => GraphNode(
        id: json['id'] as String,
        nameRu: json['name_ru'] as String,
        nameKz: json['name_kz'] as String? ?? json['name_ru'] as String,
        tag: json['tag'] as String? ?? 'other',
        zone: json['zone'] as int? ?? 3,
        status: json['status'] as String? ?? 'untested',
        pMastery: (json['p_mastery'] as num?)?.toDouble(),
        isFringe: json['is_fringe'] as bool? ?? false,
        isBlocked: json['is_blocked'] as bool? ?? false,
        difficulty: json['difficulty'] as int? ?? 1,
        downstream: json['downstream'] as int? ?? 0,
        qTotal: json['q_total'] as int? ?? 0,
        qCorrect: json['q_correct'] as int? ?? 0,
      );

  @override
  List<Object?> get props => [id, status, pMastery];
}
