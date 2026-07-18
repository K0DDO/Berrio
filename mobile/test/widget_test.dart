import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:berrio/app/app.dart';

void main() {
  testWidgets('Berrio app boots to splash/login shell', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BerrioApp()));
    await tester.pump();
    expect(find.textContaining('Berrio'), findsWidgets);
  });
}
