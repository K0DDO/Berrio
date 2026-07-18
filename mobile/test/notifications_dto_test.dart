import 'package:flutter_test/flutter_test.dart';

import 'package:berrio/features/notifications/data/notifications_api.dart';

void main() {
  test('NotificationDto parses API payload', () {
    final dto = NotificationDto.fromJson({
      'id': '11111111-1111-1111-1111-111111111111',
      'type': 'PRICE_CHANGE',
      'title': 'Цена выросла',
      'message': 'Молоко: 100₽ → 130₽ (+30%)',
      'severity': 'WARNING',
      'payload': {'delta_pct': 30, 'explanation': 'Price rose'},
      'created_at': '2026-07-18T10:00:00Z',
      'read_at': null,
    });
    expect(dto.type, 'PRICE_CHANGE');
    expect(dto.isRead, isFalse);
    expect(dto.payload['delta_pct'], 30);
  });
}
