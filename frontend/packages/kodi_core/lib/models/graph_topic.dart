import 'package:equatable/equatable.dart';

/// Тема графа (CC-кластер/НИШ-группа) — уровень между разделом и навыком.
class GraphTopic extends Equatable {
  const GraphTopic({
    required this.id,
    required this.strand,
    required this.nameRu,
    required this.nameKz,
    this.grade,
    required this.order,
    required this.prereq,
    required this.nodeIds,
  });

  final String id;
  final String strand;
  final String nameRu;
  final String nameKz;
  final int? grade;
  final int order;
  final List<String> prereq;   // id тем-предшественников
  final List<String> nodeIds;  // id узлов в этой теме

  String name(String lang) => lang == 'kz' ? nameKz : nameRu;

  factory GraphTopic.fromJson(Map<String, dynamic> json) => GraphTopic(
        id: json['id'] as String,
        strand: json['strand'] as String,
        nameRu: json['name_ru'] as String,
        nameKz: json['name_kz'] as String? ?? json['name_ru'] as String,
        grade: json['grade'] as int?,
        order: json['order'] as int? ?? 0,
        prereq: (json['prereq'] as List<dynamic>?)?.map((e) => e as String).toList() ?? const [],
        nodeIds: (json['node_ids'] as List<dynamic>?)?.map((e) => e as String).toList() ?? const [],
      );

  @override
  List<Object?> get props => [id, order, nodeIds];
}

/// Раздел графа (домен CC или НИШ) — верхний уровень иерархии.
class GraphStrand extends Equatable {
  const GraphStrand({
    required this.code,
    required this.nameRu,
    required this.nameKz,
    required this.order,
  });

  final String code;
  final String nameRu;
  final String nameKz;
  final int order;

  String name(String lang) => lang == 'kz' ? nameKz : nameRu;

  factory GraphStrand.fromJson(Map<String, dynamic> json) => GraphStrand(
        code: json['code'] as String,
        nameRu: json['name_ru'] as String,
        nameKz: json['name_kz'] as String? ?? json['name_ru'] as String,
        order: json['order'] as int? ?? 0,
      );

  @override
  List<Object?> get props => [code, order];
}
