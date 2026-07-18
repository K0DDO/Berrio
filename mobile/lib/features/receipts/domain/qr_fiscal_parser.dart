/// Parses Russian FNS QR payload strings into fiscal fields.
///
/// Example:
/// t=20240115T1230&s=250.00&fn=9281...&i=12345&fp=98765&n=1
class QrFiscalParser {
  const QrFiscalParser();

  Map<String, dynamic>? parse(String raw) {
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;

    final params = <String, String>{};
    final query = trimmed.contains('?')
        ? trimmed.substring(trimmed.indexOf('?') + 1)
        : trimmed;

    for (final part in query.split('&')) {
      final idx = part.indexOf('=');
      if (idx <= 0) continue;
      final key = Uri.decodeQueryComponent(part.substring(0, idx));
      final value = Uri.decodeQueryComponent(part.substring(idx + 1));
      params[key] = value;
    }

    final fn = params['fn'];
    final fd = params['i'] ?? params['fd'];
    final fp = params['fp'];
    if (fn == null || fd == null || fp == null) return null;

    final purchasedAt = _parseFiscalTime(params['t']);

    return {
      'fn': fn,
      'fd': fd,
      'fp': fp,
      'qrraw': query,
      if (params['s'] != null) 'total_amount': params['s'],
      if (purchasedAt != null) 'purchased_at': purchasedAt.toIso8601String(),
    };
  }

  /// FNS QR `t` is usually `YYYYMMDDTHHMM` or `YYYYMMDDTHHMMSS`.
  static DateTime? _parseFiscalTime(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final t = raw.trim();
    final match = RegExp(r'^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})?$').firstMatch(t);
    if (match != null) {
      return DateTime(
        int.parse(match.group(1)!),
        int.parse(match.group(2)!),
        int.parse(match.group(3)!),
        int.parse(match.group(4)!),
        int.parse(match.group(5)!),
        int.parse(match.group(6) ?? '0'),
      );
    }
    return DateTime.tryParse(t);
  }
}
