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

  Future<AiInsightDto> monthlyReview() async {
    final res = await _dio.get<Map<String, dynamic>>('/ai/monthly-review');
    return AiInsightDto.fromJson(res.data!);
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
        title: const Text('ИИ-экономист'),
        actions: [
          IconButton(
            tooltip: 'Разбор месяца',
            onPressed: () => _showMonthlyReview(context, ref),
            icon: const Icon(Icons.calendar_month_outlined),
          ),
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
              actionLabel: 'Разбор месяца',
              onAction: () => _showMonthlyReview(context, ref),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            itemCount: items.length + 1,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              if (index == 0) {
                return OutlinedButton.icon(
                  onPressed: () => _showMonthlyReview(context, ref),
                  icon: const Icon(Icons.calendar_month_outlined),
                  label: const Text('Разбор месяца (вторично)'),
                );
              }
              final item = items[index - 1];
              return Material(
                color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
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

  Future<void> _showMonthlyReview(BuildContext context, WidgetRef ref) async {
    try {
      final review = await ref.read(aiApiProvider).monthlyReview();
      if (!context.mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (ctx) => Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(review.title, style: Theme.of(ctx).textTheme.titleLarge),
                const SizedBox(height: 12),
                Text(review.body),
              ],
            ),
          ),
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
