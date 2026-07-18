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

    return {
      'fn': fn,
      'fd': fd,
      'fp': fp,
      if (params['s'] != null) 'total_amount': params['s'],
      if (params['t'] != null) 'purchased_at_raw': params['t'],
    };
  }
}
