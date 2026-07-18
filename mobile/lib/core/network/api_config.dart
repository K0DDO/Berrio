class ApiConfig {
  /// Production / device API base (no trailing slash).
  ///
  /// Prefer `--dart-define=API_URL=...`.
  /// Legacy alias: `--dart-define=API_BASE_URL=...` (used if API_URL is empty).
  ///
  /// Examples:
  /// - Emulator: http://10.0.2.2:8000
  /// - VPS by IP (nginx :80): http://SERVER_IP
  /// - VPS direct API: http://SERVER_IP:8000
  /// - Domain: https://api.berrio.com
  static const String _apiUrl = String.fromEnvironment('API_URL');
  static const String _apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static String get baseUrl {
    if (_apiUrl.isNotEmpty) {
      return _apiUrl;
    }
    return _apiBaseUrl;
  }

  static const String apiPrefix = '/api/v1';

  static Uri apiUri(String path) {
    final base = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    final prefix = apiPrefix.startsWith('/') ? apiPrefix : '/$apiPrefix';
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$base$prefix$p');
  }
}
