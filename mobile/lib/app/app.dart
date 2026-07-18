import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/berrio_theme.dart';
import '../features/sync/background_sync.dart';
import 'router.dart';

class BerrioApp extends ConsumerWidget {
  const BerrioApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(backgroundSyncProvider);
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Berrio',
      debugShowCheckedModeBanner: false,
      theme: BerrioTheme.light,
      routerConfig: router,
    );
  }
}
