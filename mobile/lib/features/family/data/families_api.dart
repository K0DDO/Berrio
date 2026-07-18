import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class FamilyDto {
  FamilyDto({required this.id, required this.name, required this.ownerUserId});

  final String id;
  final String name;
  final String ownerUserId;

  factory FamilyDto.fromJson(Map<String, dynamic> json) => FamilyDto(
        id: json['id'] as String,
        name: json['name'] as String,
        ownerUserId: json['owner_user_id'] as String,
      );
}

class MemberDto {
  MemberDto({
    required this.id,
    required this.userId,
    required this.role,
    required this.permissions,
  });

  final String id;
  final String userId;
  final String role;
  final Map<String, bool> permissions;

  factory MemberDto.fromJson(Map<String, dynamic> json) => MemberDto(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        role: json['role'] as String,
        permissions: Map<String, bool>.from(json['permissions'] as Map? ?? {}),
      );
}

class InviteDto {
  InviteDto({
    required this.id,
    required this.familyId,
    required this.role,
    required this.status,
    required this.expiresAt,
    required this.hasEmailLock,
    this.token,
  });

  final String id;
  final String familyId;
  final String role;
  final String status;
  final DateTime expiresAt;
  final bool hasEmailLock;
  final String? token;

  factory InviteDto.fromJson(Map<String, dynamic> json) => InviteDto(
        id: json['id'] as String,
        familyId: json['family_id'] as String,
        role: json['role'] as String,
        status: json['status'] as String,
        expiresAt: DateTime.parse(json['expires_at'] as String),
        hasEmailLock: json['has_email_lock'] as bool? ?? false,
        token: json['token'] as String?,
      );
}

class FamiliesApi {
  FamiliesApi(this._dio);

  final Dio _dio;

  Future<List<FamilyDto>> list() async {
    final res = await _dio.get<List<dynamic>>('/families');
    return (res.data ?? [])
        .map((e) => FamilyDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<FamilyDto> create(String name) async {
    final res = await _dio.post<Map<String, dynamic>>('/families', data: {'name': name});
    return FamilyDto.fromJson(res.data!);
  }

  Future<List<MemberDto>> members(String familyId) async {
    final res = await _dio.get<List<dynamic>>('/families/$familyId/members');
    return (res.data ?? [])
        .map((e) => MemberDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<InviteDto> createInvite({
    required String familyId,
    String role = 'PARENT',
    String? email,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/families/$familyId/invites',
      data: {
        'role': role,
        if (email != null && email.isNotEmpty) 'email': email,
      },
    );
    return InviteDto.fromJson(res.data!);
  }

  Future<List<InviteDto>> listInvites(String familyId) async {
    final res = await _dio.get<List<dynamic>>('/families/$familyId/invites');
    return (res.data ?? [])
        .map((e) => InviteDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<MemberDto> acceptInvite(String token) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/families/invites/accept',
      data: {'token': token},
    );
    return MemberDto.fromJson(res.data!);
  }

  Future<void> revokeInvite(String familyId, String inviteId) async {
    await _dio.delete('/families/$familyId/invites/$inviteId');
  }
}

final familiesApiProvider = Provider<FamiliesApi>((ref) {
  return FamiliesApi(ref.watch(dioProvider));
});

final familiesListProvider = FutureProvider.autoDispose<List<FamilyDto>>((ref) {
  return ref.watch(familiesApiProvider).list();
});
