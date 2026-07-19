import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Local unlock preference (biometric or PIN).
///
/// **Security note:** the account password is never stored here.
/// For PIN unlock we only persist `sha256(pin + salt)` — the raw PIN is not saved.
enum UnlockMethod { biometric, pin }

class UnlockConfig {
  const UnlockConfig({
    required this.enabled,
    this.method,
  });

  final bool enabled;
  final UnlockMethod? method;

  static const disabled = UnlockConfig(enabled: false);
}

/// Persists unlock_enabled / unlock_method / pin_hash (+ salt) in secure storage.
class LocalUnlockStore {
  LocalUnlockStore(this._storage);

  final FlutterSecureStorage _storage;

  static const _enabledKey = 'berrio_unlock_enabled';
  static const _methodKey = 'berrio_unlock_method';
  static const _pinHashKey = 'berrio_unlock_pin_hash';
  static const _saltKey = 'berrio_unlock_pin_salt';

  Future<UnlockConfig> readConfig() async {
    final enabled = await _storage.read(key: _enabledKey) == '1';
    if (!enabled) return UnlockConfig.disabled;
    final methodRaw = await _storage.read(key: _methodKey);
    final method = switch (methodRaw) {
      'biometric' => UnlockMethod.biometric,
      'pin' => UnlockMethod.pin,
      _ => null,
    };
    return UnlockConfig(enabled: true, method: method);
  }

  Future<void> enableBiometric() async {
    await _storage.write(key: _enabledKey, value: '1');
    await _storage.write(key: _methodKey, value: 'biometric');
    await _storage.delete(key: _pinHashKey);
    await _storage.delete(key: _saltKey);
  }

  /// Stores only a salted SHA-256 hash of the PIN — never the PIN or account password.
  Future<void> enablePin(String pin) async {
    final salt = _generateSalt();
    final hash = hashPin(pin, salt);
    await _storage.write(key: _enabledKey, value: '1');
    await _storage.write(key: _methodKey, value: 'pin');
    await _storage.write(key: _saltKey, value: salt);
    await _storage.write(key: _pinHashKey, value: hash);
  }

  Future<bool> verifyPin(String pin) async {
    final salt = await _storage.read(key: _saltKey);
    final expected = await _storage.read(key: _pinHashKey);
    if (salt == null || expected == null) return false;
    return hashPin(pin, salt) == expected;
  }

  Future<void> disable() async {
    await _storage.delete(key: _enabledKey);
    await _storage.delete(key: _methodKey);
    await _storage.delete(key: _pinHashKey);
    await _storage.delete(key: _saltKey);
  }

  static String hashPin(String pin, String salt) {
    return sha256.convert(utf8.encode('$pin$salt')).toString();
  }

  String _generateSalt() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    return base64UrlEncode(bytes).replaceAll('=', '');
  }
}

final localUnlockStoreProvider = Provider<LocalUnlockStore>((ref) {
  return LocalUnlockStore(const FlutterSecureStorage());
});

/// Loaded during splash; null while still reading secure storage.
final unlockConfigProvider = StateProvider<UnlockConfig?>((ref) => null);

/// In-memory: cleared on process restart / logout. Gates the app when unlock is enabled.
final sessionUnlockedProvider = StateProvider<bool>((ref) => false);
