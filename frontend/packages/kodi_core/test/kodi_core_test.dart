import 'package:flutter_test/flutter_test.dart';
import 'package:kodi_core/kodi_core.dart';

void main() {
  group('NisApiClient', () {
    test('can be instantiated', () {
      final client = NisApiClient(baseUrl: 'http://localhost:8000');
      expect(client, isNotNull);
    });
  });
}
