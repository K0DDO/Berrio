import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/storage/secure_token_store.dart';
import '../data/auth_api.dart';
import '../data/auth_models.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  const AuthState({
    required this.status,
    this.user,
    this.error,
  });

  final AuthStatus status;
  final AuthUser? user;
  final String? error;

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    String? error,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._api, this._tokens) : super(const AuthState(status: AuthStatus.unknown));

  final AuthApi _api;
  final SecureTokenStore _tokens;

  Future<void> bootstrap() async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }
    try {
      final deviceId = await _tokens.getOrCreateDeviceId();
      final pair = await _api.refresh(refreshToken: refresh, deviceId: deviceId);
      await _tokens.saveSession(
        accessToken: pair.accessToken,
        refreshToken: pair.refreshToken,
      );
      state = AuthState(status: AuthStatus.authenticated, user: pair.user);
    } catch (_) {
      await _tokens.clear();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    state = state.copyWith(clearError: true);
    try {
      final deviceId = await _tokens.getOrCreateDeviceId();
      final pair = await _api.register(
        email: email,
        password: password,
        displayName: displayName,
        deviceId: deviceId,
        deviceName: 'Berrio Flutter',
      );
      await _tokens.saveSession(
        accessToken: pair.accessToken,
        refreshToken: pair.refreshToken,
      );
      state = AuthState(status: AuthStatus.authenticated, user: pair.user);
    } on DioException catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: _messageFromDio(e),
      );
    }
  }

  Future<void> login({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(clearError: true);
    try {
      final deviceId = await _tokens.getOrCreateDeviceId();
      final pair = await _api.login(
        email: email,
        password: password,
        deviceId: deviceId,
        deviceName: 'Berrio Flutter',
      );
      await _tokens.saveSession(
        accessToken: pair.accessToken,
        refreshToken: pair.refreshToken,
      );
      state = AuthState(status: AuthStatus.authenticated, user: pair.user);
    } on DioException catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: _messageFromDio(e),
      );
    }
  }

  Future<void> logout() async {
    final refresh = await _tokens.readRefreshToken();
    final deviceId = await _tokens.getOrCreateDeviceId();
    if (refresh != null) {
      try {
        await _api.logout(refreshToken: refresh, deviceId: deviceId);
      } catch (_) {
        // Still clear local session.
      }
    }
    await _tokens.clear();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Called when API refresh fails — drop UI session so user returns to login.
  void markSessionExpired() {
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  String _messageFromDio(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString();
    }
    return e.message ?? 'Authentication failed';
  }
}

final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(ref.watch(dioProvider));
});

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    ref.watch(authApiProvider),
    ref.watch(secureTokenStoreProvider),
  );
});
