import 'package:flutter_test/flutter_test.dart';

import 'package:berrio/features/receipts/data/receipts_api.dart';

void main() {
  test('ReceiptDto parses categories and price change', () {
    final dto = ReceiptDto.fromJson({
      'id': 'r1',
      'fn': '1',
      'fd': '2',
      'fp': '3',
      'status': 'done',
      'store_name': 'Пятёрочка',
      'total_amount': '250.00',
      'purchased_at': '2024-01-15T12:00:00Z',
      'items': [
        {
          'id': 'i1',
          'name_raw': 'Молоко',
          'qty': '1',
          'price': '89',
          'sum': '89',
          'category_id': 'c1',
          'category_name': 'Продукты',
          'previous_price': '80',
          'price_change_pct': 11.3,
        },
      ],
    });

    expect(dto.storeName, 'Пятёрочка');
    expect(dto.items.single.categoryName, 'Продукты');
    expect(dto.items.single.previousPrice, '80');
    expect(dto.items.single.priceChangePct, 11.3);
  });

  test('ReceiptDto parses warnings, requires_confirmation, name_display', () {
    final dto = ReceiptDto.fromJson({
      'id': 'r2',
      'fn': '1',
      'fd': '2',
      'fp': '3',
      'status': 'needs_confirmation',
      'requires_confirmation': true,
      'warnings': ['Проверьте дату', 'Сумма позиций не сходится с итогом'],
      'items': [
        {
          'id': 'i1',
          'name_raw': 'МОЛОКО ПРОСТОКВАШИНО 2.5% 1098478218914',
          'name_display': 'Молоко Простоквашино 2.5%',
          'qty': '1',
          'price': '89',
          'sum': '89',
        },
      ],
    });

    expect(dto.requiresConfirmation, isTrue);
    expect(dto.warnings, hasLength(2));
    expect(dto.items.single.nameDisplay, 'Молоко Простоквашино 2.5%');
  });
}
