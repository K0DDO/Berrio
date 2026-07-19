import 'package:flutter/material.dart';

/// Shared empty / error / offline panels for journey screens.
class JourneyStatePanel extends StatelessWidget {
  const JourneyStatePanel({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  factory JourneyStatePanel.empty({
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return JourneyStatePanel(
      icon: Icons.inbox_outlined,
      title: title,
      message: message,
      actionLabel: actionLabel,
      onAction: onAction,
    );
  }

  factory JourneyStatePanel.error({
    required String message,
    VoidCallback? onRetry,
  }) {
    return JourneyStatePanel(
      icon: Icons.error_outline,
      title: 'Что-то пошло не так',
      message: message,
      actionLabel: onRetry == null ? null : 'Повторить',
      onAction: onRetry,
    );
  }

  factory JourneyStatePanel.offline({
    String? message,
    VoidCallback? onRetry,
  }) {
    return JourneyStatePanel(
      icon: Icons.cloud_off_outlined,
      title: 'You are offline',
      message: message ??
          'Changes are saved locally and will sync when you are back online.',
      actionLabel: onRetry == null ? null : 'Try sync',
      onAction: onRetry,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: scheme.primary.withValues(alpha: 0.7)),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: scheme.onSurface.withValues(alpha: 0.65),
                    height: 1.4,
                  ),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 20),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
