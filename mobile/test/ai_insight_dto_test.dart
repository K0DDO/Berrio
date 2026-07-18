import 'package:flutter_test/flutter_test.dart';

import 'package:berrio/features/ai/presentation/ai_screen.dart';

void main() {
  test('AiInsightDto parses id and body', () {
    final dto = AiInsightDto.fromJson({
      'id': '11111111-1111-1111-1111-111111111111',
      'title': 'Первый разбор трат',
      'body': 'За последние 30 дней…',
      'kind': 'first_insight',
    });
    expect(dto.id, isNotNull);
    expect(dto.kind, 'first_insight');
  });
}
