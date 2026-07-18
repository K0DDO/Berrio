import 'dart:convert';
import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists refresh token + device id. Access token stays in memory.
class SecureTokenStore {
  SecureTokenStore(this._storage);

  final FlutterSecureStorage _storage;

  static const _refreshKey = 'berrio_refresh_token';
  static const _deviceKey = 'berrio_device_id';
  String? _accessToken;

  String? get accessToken => _accessToken;

  Future<void> saveSession({
    required String accessToken,
    required String refreshToken,
  }) async {
    _accessToken = accessToken;
    await _storage.write(key: _refreshKey, value: refreshToken);
  }

  Future<void> saveAccessToken(String accessToken) async {
    _accessToken = accessToken;
  }

  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  Future<String> getOrCreateDeviceId() async {
    final existing = await _storage.read(key: _deviceKey);
    if (existing != null && existing.length >= 8) return existing;
    final id = _generateDeviceId();
    await _storage.write(key: _deviceKey, value: id);
    return id;
  }

  Future<void> clear() async {
    _accessToken = null;
    await _storage.delete(key: _refreshKey);
  }

  String _generateDeviceId() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    return base64UrlEncode(bytes).replaceAll('=', '');
  }
}

final secureTokenStoreProvider = Provider<SecureTokenStore>((ref) {
  return SecureTokenStore(const FlutterSecureStorage());
});
