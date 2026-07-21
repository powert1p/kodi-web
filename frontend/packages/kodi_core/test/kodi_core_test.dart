import 'package:flutter_test/flutter_test.dart';
import 'package:kodi_core/kodi_core.dart';

void main() {
  group('NisApiClient', () {
    test('can be instantiated', () {
      final client = NisApiClient(baseUrl: 'http://localhost:8000');
      expect(client, isNotNull);
    });

    test('creates distinct bounded ids for retry-safe answer submissions', () {
      final client = NisApiClient(baseUrl: 'http://localhost:8000');

      final first = client.newClientAttemptId('practice');
      final second = client.newClientAttemptId('practice');

      expect(first, isNot(second));
      expect(first, startsWith('practice-'));
      expect(first.length, lessThanOrEqualTo(64));
      expect(second.length, lessThanOrEqualTo(64));
    });
  });
}
