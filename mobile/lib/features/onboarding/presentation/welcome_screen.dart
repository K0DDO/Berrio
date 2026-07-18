import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/router.dart';
import '../../../core/storage/secure_token_store.dart';

/// First-launch value proposition before auth.
class WelcomeScreen extends ConsumerWidget {
  const WelcomeScreen({super.key});

  Future<void> _finishOnboarding(WidgetRef ref, String path) async {
    await ref.read(secureTokenStoreProvider).markOnboardingSeen();
    ref.read(onboardingSeenProvider.notifier).state = true;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Berrio',
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                      color: scheme.primary,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 12),
              Text(
                'Личный финансовый ассистент',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 12),
              Text(
                'Сканируйте чеки, понимайте траты и цели — без ручного ввода и без стыда за покупки.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: scheme.onSurface.withValues(alpha: 0.7),
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 36),
              const _ValueRow(
                icon: Icons.qr_code_scanner,
                title: 'Автозахват',
                subtitle: 'QR чека → категории и цены сами',
              ),
              const _ValueRow(
                icon: Icons.favorite_outline,
                title: 'Berrio Score',
                subtitle: 'Здоровье денег как понятная оценка',
              ),
              const _ValueRow(
                icon: Icons.family_restroom,
                title: 'Семья',
                subtitle: 'Роли и безопасный контур для детей',
              ),
              const Spacer(),
              FilledButton(
                onPressed: () async {
                  await _finishOnboarding(ref, '/register');
                  if (context.mounted) context.go('/register');
                },
                child: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 4),
                  child: Text('Начать'),
                ),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () async {
                  await _finishOnboarding(ref, '/login');
                  if (context.mounted) context.go('/login');
                },
                child: const Text('У меня уже есть аккаунт'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ValueRow extends StatelessWidget {
  const _ValueRow({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: scheme.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: scheme.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: scheme.onSurface.withValues(alpha: 0.65),
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
