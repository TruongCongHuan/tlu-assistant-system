// lib/theme/app_theme.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // ── Color palette (from Gemini dark UI) ──────────────
  static const Color background    = Color(0xFF0D0D0D);
  static const Color surface       = Color(0xFF1A1A1A);
  static const Color surfaceHigh   = Color(0xFF262626);
  static const Color surfaceBorder = Color(0xFF333333);
  static const Color accent        = Color(0xFF8AB4F8);   // Gemini blue
  static const Color accentGreen   = Color(0xFF81C995);   // Success
  static const Color accentRed     = Color(0xFFF28B82);   // Error / recording
  static const Color textPrimary   = Color(0xFFE8EAED);
  static const Color textSecondary = Color(0xFF9AA0A6);
  static const Color textTertiary  = Color(0xFF5F6368);
  static const Color userBubble    = Color(0xFF1E3A5F);   // User msg bg
  static const Color aiBubble      = Color(0xFF1E1E1E);   // AI msg bg

  static ThemeData get dark {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: accent,
        secondary: accentGreen,
        error: accentRed,
        surface: surface,
      ),
      textTheme: GoogleFonts.notoSansTextTheme(ThemeData.dark().textTheme)
          .apply(bodyColor: textPrimary, displayColor: textPrimary),
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        systemOverlayStyle: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
        ),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w500,
          letterSpacing: 0.15,
        ),
      ),
      drawerTheme: const DrawerThemeData(backgroundColor: surface),
      dividerTheme: const DividerThemeData(color: surfaceBorder, thickness: 1),
      iconTheme: const IconThemeData(color: textSecondary),
      splashColor: Colors.white.withOpacity(0.05),
      highlightColor: Colors.white.withOpacity(0.03),
    );
  }
}
