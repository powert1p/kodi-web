import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary = Color(0xFF2563EB);      // blue-600
  static const Color secondary = Color(0xFF10B981);    // emerald-500
  static const Color error = Color(0xFFEF4444);        // red-500
  static const Color warning = Color(0xFFF59E0B);      // amber-500
  static const Color surface = Color(0xFFF8FAFC);      // slate-50
  static const Color card = Colors.white;

  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primary,
          surface: surface,
        ),
        cardTheme: const CardThemeData(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16)),
            side: BorderSide(color: Color(0xFFE2E8F0)),
          ),
        ),
        appBarTheme: const AppBarTheme(
          elevation: 0,
          backgroundColor: Colors.white,
          foregroundColor: Color(0xFF1E293B),
          surfaceTintColor: Colors.transparent,
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size(200, 52),
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(12)),
            ),
          ),
        ),
      );
}
