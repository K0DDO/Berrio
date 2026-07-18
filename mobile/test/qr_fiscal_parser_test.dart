import 'package:flutter_test/flutter_test.dart';
import 'package:berrio/features/receipts/domain/qr_fiscal_parser.dart';

void main() {
  const parser = QrFiscalParser();

  test('parses FNS QR query string', () {
    final result = parser.parse(
      't=20240115T1200&s=250.00&fn=9281000100123456&i=12345&fp=987654321&n=1',
    );
    expect(result, isNotNull);
    expect(result!['fn'], '9281000100123456');
    expect(result['fd'], '12345');
    expect(result['fp'], '987654321');
    expect(result['total_amount'], '250.00');
    expect(result['purchased_at'], isNotNull);
    expect(result['purchased_at'], contains('2024-01-15'));
    expect(result['qrraw'], contains('fn=9281000100123456'));
  });

  test('rejects incomplete payload', () {
    expect(parser.parse('fn=1&fp=2'), isNull);
  });
}
