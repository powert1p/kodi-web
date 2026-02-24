import 'package:kodi_core/kodi_core.dart';

class SectionData {
  const SectionData({
    required this.tag,
    required this.nameRu,
    required this.icon,
    required this.testedCount,
    required this.totalCount,
    required this.percentage,
    required this.barGreen,
    required this.barRed,
    required this.barGray,
    required this.topics,
    required this.problemsSolved,
    required this.problemsCorrect,
  });

  final String tag, nameRu, icon;
  final int testedCount, totalCount, percentage;
  final double barGreen, barRed, barGray;
  final List<GraphNode> topics;
  final int problemsSolved, problemsCorrect;
}
