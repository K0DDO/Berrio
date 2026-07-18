class ApiConfig {
  /// Override via --dart-define=API_BASE_URL=
  ///
  /// Defaults:
  /// - Android emulator → host loopback bridge
  /// - Physical device / iOS: pass LAN IP or https://api.domain
  /// See docs/device-testing.md and docs/vps-deployment.md
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String apiPrefix = '/api/v1';

  static Uri apiUri(String path) {
    final base = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    final prefix = apiPrefix.startsWith('/') ? apiPrefix : '/$apiPrefix';
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$base$prefix$p');
  }
}
