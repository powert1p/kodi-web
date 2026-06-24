import 'package:flutter_test/flutter_test.dart';
import 'package:kodi_core/kodi_core.dart';

void main() {
  test('GraphTopic.fromJson parses prereq and nodeIds', () {
    final t = GraphTopic.fromJson({
      'id': '6.RP.A', 'strand': 'RP', 'grade': 6, 'order': 10,
      'name_ru': 'Отношения', 'name_kz': 'Қатынастар',
      'prereq': ['4.MD.A'], 'node_ids': ['PR01', 'PC01'],
    });
    expect(t.id, '6.RP.A');
    expect(t.prereq, ['4.MD.A']);
    expect(t.nodeIds.length, 2);
    expect(t.name('kz'), 'Қатынастар');
  });

  test('GraphStrand.name picks lang', () {
    final s = GraphStrand.fromJson(
        {'code': 'RP', 'name_ru': 'Отношения', 'name_kz': 'Қатынастар', 'order': 1});
    expect(s.name('ru'), 'Отношения');
  });

  test('GraphNode.fromJson parses topicId', () {
    final n = GraphNode.fromJson({
      'id': 'PR01', 'name_ru': 'a', 'name_kz': 'b', 'tag': 'proportion',
      'zone': 1, 'status': 'untested', 'topic_id': '6.RP.A',
    });
    expect(n.topicId, '6.RP.A');
  });
}
