import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/secure_token_store.dart';
import 'api_config.dart';

final dioProvider = Provider<Dio>((ref) {
  final tokens = ref.watch(secureTokenStoreProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: '${ApiConfig.baseUrl}${ApiConfig.apiPrefix}',
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Accept': 'application/json'},
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final access = tokens.accessToken;
        if (access != null && access.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $access';
        }
        final deviceId = await tokens.getOrCreateDeviceId();
        options.headers['X-Device-Id'] = deviceId;
        handler.next(options);
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

        final refresh = await tokens.readRefreshToken();
        if (refresh == null) {
          return handler.next(error);
        }

        try {
          final deviceId = await tokens.getOrCreateDeviceId();
          final refreshDio = Dio(
            BaseOptions(baseUrl: '${ApiConfig.baseUrl}${ApiConfig.apiPrefix}'),
          );
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
          await tokens.saveSession(
            accessToken: newAccess,
            refreshToken: newRefresh,
          );

          final req = error.requestOptions;
          req.headers['Authorization'] = 'Bearer $newAccess';
          final retry = await dio.fetch(req);
          return handler.resolve(retry);
        } catch (_) {
          await tokens.clear();
          return handler.next(error);
        }
      },
    ),
  );

  return dio;
});
