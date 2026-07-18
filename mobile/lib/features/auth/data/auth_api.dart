import 'package:dio/dio.dart';

import 'auth_models.dart';

class AuthApi {
  AuthApi(this._dio);

  final Dio _dio;

  Future<TokenPair> register({
    required String email,
    required String password,
    required String displayName,
    required String deviceId,
    String? deviceName,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/register',
      data: {
        'email': email,
        'password': password,
        'display_name': displayName,
        'device_id': deviceId,
        'device_name': deviceName,
      },
    );
    return TokenPair.fromJson(response.data!);
  }

  Future<TokenPair> login({
    required String email,
    required String password,
    required String deviceId,
    String? deviceName,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {
        'email': email,
        'password': password,
        'device_id': deviceId,
        'device_name': deviceName,
      },
    );
    return TokenPair.fromJson(response.data!);
  }

  Future<TokenPair> refresh({
    required String refreshToken,
    required String deviceId,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: {
        'refresh_token': refreshToken,
        'device_id': deviceId,
      },
    );
    return TokenPair.fromJson(response.data!);
  }

  Future<void> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    await _dio.post<void>(
      '/auth/logout',
      data: {
        'refresh_token': refreshToken,
        'device_id': deviceId,
      },
    );
  }

  Future<AuthUser> me() async {
    final response = await _dio.get<Map<String, dynamic>>('/auth/me');
    return AuthUser.fromJson(response.data!);
  }
}
