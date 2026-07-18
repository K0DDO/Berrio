class ApiConfig {
  /// Android emulator → host machine. Override via --dart-define=API_BASE_URL=
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String apiPrefix = '/api/v1';
}
