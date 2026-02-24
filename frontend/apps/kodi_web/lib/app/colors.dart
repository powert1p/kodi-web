import 'package:flutter/material.dart';

/// Centralized color palette for the entire app.
///
/// Replaces 25+ scattered Color(0xFF...) literals.
/// Usage: `AppColors.primary`, `AppColors.success`, etc.
abstract final class AppColors {
  // ── Brand ──
  static const Color primary = Color(0xFF2563EB);       // blue-600
  static const Color success = Color(0xFF10B981);        // emerald-500
  static const Color error = Color(0xFFEF4444);          // red-500
  static const Color warning = Color(0xFFF59E0B);        // amber-500
  static const Color purple = Color(0xFF7C3AED);         // violet-600

  // ── Text ──
  static const Color textPrimary = Color(0xFF1E293B);    // slate-800
  static const Color textSecondary = Color(0xFF64748B);  // slate-500
  static const Color textBody = Color(0xFF475569);       // slate-600

  // ── Surfaces ──
  static const Color scaffoldBg = Color(0xFFFAF9F6);    // warm white
  static const Color surface = Color(0xFFF8FAFC);        // slate-50
  static const Color surfaceAlt = Color(0xFFF1F5F9);    // slate-100
  static const Color card = Colors.white;

  // ── Borders / muted ──
  static const Color border = Color(0xFFE2E8F0);        // slate-200
  static const Color borderLight = Color(0xFFCBD5E1);   // slate-300
  static const Color muted = Color(0xFF94A3B8);          // slate-400

  // ── Light tinted backgrounds ──
  static const Color primaryBgLight = Color(0xFFEFF6FF); // blue-50
  static const Color successBgLight = Color(0xFFECFDF5); // emerald-50
  static const Color errorBgLight = Color(0xFFFEF2F2);  // red-50

  // ── Accent ──
  static const Color orange = Color(0xFFFFA726);         // orange-400
  static const Color comboStart = Color(0xFFFF6B35);     // combo gradient
  static const Color comboEnd = Color(0xFFFF8F00);       // combo gradient

  // ── Progress / traffic-light ──
  static const Color progressGreen = Color(0xFF4CAF50);  // Material green
  static const Color progressOrange = Color(0xFFFF9800); // Material orange
  static const Color progressRed = Color(0xFFF44336);    // Material red
  static const Color progressGray = Color(0xFFE0E0E0);   // grey-300

  // ── Gradients ──
  static const Color heroGradientStart = Color(0xFF1D4ED8); // blue-700
  static const Color heroGradientEnd = Color(0xFF3B82F6);   // blue-500
  static const Color gradientPurpleStart = Color(0xFF667EEA);
  static const Color gradientPurpleEnd = Color(0xFF764BA2);

  // ── Misc ──
  static const Color purpleLight = Color(0xFF8B5CF6);    // violet-500
  static const Color telegram = Color(0xFF229ED9);        // Telegram brand
  static const Color warningBgLight = Color(0xFFFFF7ED); // orange-50
  static const Color loginBg = Color(0xFFF0F4FF);        // blue-50
  static const Color infoBlueDark = Color(0xFF1E40AF);   // blue-800
  static const Color infoGreenDark = Color(0xFF166534);  // green-800
  static const Color orangeGradient = Color(0xFFF97316); // orange-500

  // ── Leaderboard ──
  static const Color leaderboardActiveBg = Color(0xFFFFF3E0);
  static const Color leaderboardActiveText = Color(0xFFE65100);
  static const Color leaderboardHighlightBg = Color(0xFFFFF8E1);
  static const Color leaderboardHighlightBorder = Color(0xFFFFB300);
}
