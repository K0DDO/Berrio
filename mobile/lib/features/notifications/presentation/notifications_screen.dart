import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../data/notifications_api.dart';
import '../../sync/sync_providers.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationsListProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () => ref.invalidate(notificationsListProvider),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed: $e')),
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Text(
                'No alerts yet.\nBerrio will explain money events here.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: scheme.onSurface.withValues(alpha: 0.6),
                    ),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final n = items[index];
              return _NotificationCard(
                notification: n,
                onTap: () async {
                  if (!n.isRead) {
                    final now = DateTime.now().toUtc();
                    await ref
                        .read(localNotificationsDaoProvider)
                        .markReadLocal(n.id, now);
                    try {
                      await ref.read(notificationsApiProvider).markRead(n.id);
                    } catch (_) {
                      await ref
                          .read(syncEngineProvider)
                          .enqueueNotificationRead(n.id);
                    }
                    ref.invalidate(notificationsListProvider);
                  }
                },
              );
            },
          );
        },
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({
    required this.notification,
    required this.onTap,
  });

  final NotificationDto notification;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final meta = _metaFor(notification.type, notification.severity, scheme);
    final time = DateFormat('d MMM, HH:mm').format(notification.createdAt.toLocal());
    final unread = !notification.isRead;

    return Material(
      color: unread ? Colors.white : scheme.surface.withValues(alpha: 0.7),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: meta.color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(meta.icon, color: meta.color, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            notification.title,
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                  fontWeight: unread ? FontWeight.w700 : FontWeight.w500,
                                ),
                          ),
                        ),
                        if (unread)
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: scheme.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      notification.message,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: scheme.onSurface.withValues(alpha: 0.75),
                            height: 1.35,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      time,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: scheme.onSurface.withValues(alpha: 0.45),
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static ({IconData icon, Color color}) _metaFor(
    String type,
    String severity,
    ColorScheme scheme,
  ) {
    final critical = severity == 'CRITICAL';
    final warning = severity == 'WARNING';
    return switch (type) {
      'BUDGET_EXCEEDED' => (
          icon: Icons.warning_amber_rounded,
          color: scheme.error,
        ),
      'BUDGET_WARNING' => (
          icon: Icons.pie_chart_outline,
          color: warning ? const Color(0xFFC47B1A) : scheme.primary,
        ),
      'PRICE_CHANGE' => (
          icon: Icons.trending_up,
          color: const Color(0xFFC47B1A),
        ),
      'GOAL_PROGRESS' => (
          icon: Icons.flag_outlined,
          color: scheme.primary,
        ),
      'UNUSUAL_SPENDING' => (
          icon: Icons.shopping_bag_outlined,
          color: critical ? scheme.error : const Color(0xFFC47B1A),
        ),
      'AI_INSIGHT' => (
          icon: Icons.auto_awesome,
          color: scheme.primary,
        ),
      _ => (icon: Icons.notifications_outlined, color: scheme.primary),
    };
  }
}
