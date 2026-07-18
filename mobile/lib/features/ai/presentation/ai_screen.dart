import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../../shared/widgets/journey_state_panel.dart';

class AiInsightDto {
  AiInsightDto({
    required this.id,
    required this.title,
    required this.body,
    required this.kind,
  });

  final String? id;
  final String title;
  final String body;
  final String kind;

  factory AiInsightDto.fromJson(Map<String, dynamic> json) => AiInsightDto(
        id: json['id']?.toString(),
        title: json['title'] as String? ?? '',
        body: json['body'] as String? ?? '',
        kind: json['kind'] as String? ?? '',
      );
}

class AiApi {
  AiApi(this._dio);

  final Dio _dio;

  Future<List<AiInsightDto>> insights() async {
    final res = await _dio.get<List<dynamic>>('/ai/insights');
    return (res.data ?? [])
        .map((e) => AiInsightDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<void> feedback(String insightId, {required bool helpful}) async {
    await _dio.post(
      '/ai/insights/$insightId/feedback',
      data: {'feedback_type': helpful ? 'HELPFUL' : 'NOT_HELPFUL'},
    );
  }
}

final aiApiProvider = Provider<AiApi>((ref) => AiApi(ref.watch(dioProvider)));

final aiInsightsProvider = FutureProvider.autoDispose<List<AiInsightDto>>((ref) {
  return ref.watch(aiApiProvider).insights();
});

class AiScreen extends ConsumerWidget {
  const AiScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(aiInsightsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Economist'),
        actions: [
          IconButton(
            onPressed: () => ref.invalidate(aiInsightsProvider),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(aiInsightsProvider),
        ),
        data: (items) {
          if (items.isEmpty) {
            return JourneyStatePanel.empty(
              title: 'No insights yet',
              message: 'Scan a few receipts — Berrio will explain your spending.',
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final item = items[index];
              return Material(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(item.body),
                      if (item.id != null) ...[
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            TextButton.icon(
                              onPressed: () async {
                                await ref.read(aiApiProvider).feedback(item.id!, helpful: true);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Thanks — marked helpful')),
                                  );
                                }
                              },
                              icon: const Icon(Icons.thumb_up_alt_outlined, size: 18),
                              label: const Text('Helpful'),
                            ),
                            TextButton.icon(
                              onPressed: () async {
                                await ref.read(aiApiProvider).feedback(item.id!, helpful: false);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Noted — will improve')),
                                  );
                                }
                              },
                              icon: const Icon(Icons.thumb_down_alt_outlined, size: 18),
                              label: const Text('Not helpful'),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
