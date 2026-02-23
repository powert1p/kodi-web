import 'package:flutter_test/flutter_test.dart';
import 'package:kodi_web/main.dart';

void main() {
  testWidgets('App smoke test', (tester) async {
    await tester.pumpWidget(const NisMathApp());
    expect(find.byType(NisMathApp), findsOneWidget);
  });
}
