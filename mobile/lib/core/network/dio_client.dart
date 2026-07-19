import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/secure_token_store.dart';
import 'api_config.dart';

/// Single-flight refresh so parallel 401s don't rotate the refresh token twice.
class _SessionRefresher {
  _SessionRefresher(this._tokens);

  final SecureTokenStore _tokens;
  Future<String>? _inFlight;

  Future<String?> ensureAccessToken({required Dio refreshDio}) async {
    final current = _tokens.accessToken;
    if (current != null && current.isNotEmpty) return current;
    return refresh(refreshDio: refreshDio);
  }

  Future<String?> refresh({required Dio refreshDio}) async {
    if (_inFlight != null) return _inFlight;

    final future = _doRefresh(refreshDio);
    _inFlight = future;
    try {
      return await future;
    } finally {
      if (identical(_inFlight, future)) {
        _inFlight = null;
      }
    }
  }

  Future<String> _doRefresh(Dio refreshDio) async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null || refresh.isEmpty) {
      throw StateError('No refresh token');
    }
    final deviceId = await _tokens.getOrCreateDeviceId();
    final response = await refreshDio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: {
        'refresh_token': refresh,
        'device_id': deviceId,
      },
    );
    final data = response.data!;
    final newAccess = data['access_token'] as String;
    final newRefresh = data['refresh_token'] as String;
    await _tokens.saveSession(
      accessToken: newAccess,
      refreshToken: newRefresh,
    );
    return newAccess;
  }
}

final dioProvider = Provider<Dio>((ref) {
  final tokens = ref.watch(secureTokenStoreProvider);
  final refresher = _SessionRefresher(tokens);

  final dio = Dio(
    BaseOptions(
      baseUrl: '${ApiConfig.baseUrl}${ApiConfig.apiPrefix}',
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 60),
      sendTimeout: const Duration(seconds: 60),
      headers: {'Accept': 'application/json'},
    ),
  );

  Dio refreshDio() => Dio(
        BaseOptions(
          baseUrl: '${ApiConfig.baseUrl}${ApiConfig.apiPrefix}',
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        try {
          final access = await refresher.ensureAccessToken(refreshDio: refreshDio());
          if (access != null && access.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $access';
          }
          final deviceId = await tokens.getOrCreateDeviceId();
          options.headers['X-Device-Id'] = deviceId;
          handler.next(options);
        } catch (_) {
          handler.next(options);
        }
      },
      onError: (error, handler) async {
        final status = error.response?.statusCode;
        final path = error.requestOptions.path;
        final isAuthPath = path.contains('/auth/login') ||
            path.contains('/auth/register') ||
            path.contains('/auth/refresh');

        if (status != 401 || isAuthPath) {
          return handler.next(error);
        }

        try {
          final newAccess = await refresher.refresh(refreshDio: refreshDio());
          if (newAccess == null || newAccess.isEmpty) {
            return handler.next(error);
          }

          final req = error.requestOptions;
          // Multipart streams can't be replayed — caller must retry the upload.
          if (req.data is FormData) {
            return handler.next(error);
          }

          req.headers['Authorization'] = 'Bearer $newAccess';
          final retry = await dio.fetch(req);
          return handler.resolve(retry);
        } on DioException catch (e) {
          // Only wipe session when refresh itself is rejected.
          if (e.response?.statusCode == 401) {
            await tokens.clear();
          }
          return handler.next(error);
        } catch (_) {
          return handler.next(error);
        }
      },
    ),
  );

  return dio;
});
