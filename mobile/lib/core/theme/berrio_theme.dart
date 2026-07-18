import 'package:flutter/material.dart';

/// Calm fintech palette — green berry accent, not purple-default AI look.
class BerrioTheme {
  static const Color _seed = Color(0xFF1F6F5B);
  static const Color _surface = Color(0xFFF6F8F7);

  static ThemeData get light {
    final base = ColorScheme.fromSeed(
      seedColor: _seed,
      brightness: Brightness.light,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: base.copyWith(surface: _surface),
      scaffoldBackgroundColor: _surface,
      appBarTheme: AppBarTheme(
        backgroundColor: _surface,
        foregroundColor: base.onSurface,
        elevation: 0,
        centerTitle: false,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: _seed.withValues(alpha: 0.12),
      ),
      fontFamily: 'Segoe UI',
    );
  }
}
