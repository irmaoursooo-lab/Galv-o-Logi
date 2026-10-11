import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Design Tokens Oficiais da Apple para o Cockpit Galvão Logi
class AppleTokens {
  static const Color deepSpaceBlack = Color(0xFF0A0A0C);
  static const Color pureDaylightBg = Color(0xFFF5F5F7);
  static const Color elevatedSurfaceDark = Color(0xFF1C1C1E);
  static const Color systemGreen = Color(0xFF30D158);
  static const Color navigationBlue = Color(0xFF0071E3);
  static const Color amberCaution = Color(0xFFFF9F0A);
  static const Color coralRed = Color(0xFFFF453A);

  static const Color textPrimaryDark = Color(0xFFF5F5F7);
  static const Color textSecondaryDark = Color(0xFF86868B);
  static const Color hairlineBorderDark = Color(0x1FFFFFFF);

  static final BorderRadius capsuleRadius = BorderRadius.circular(100.0);
  static final BorderRadius cardRadius = BorderRadius.circular(22.0);

  /// Componente nativo de Vidro Fosco Translúcido (Cupertino Glassmorphism)
  static Widget frostedGlassContainer({
    required Widget child,
    EdgeInsetsGeometry padding = const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
    double blurSigma = 20.0,
    bool isDarkMode = true,
  }) {
    return ClipRRect(
      borderRadius: cardRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: Container(
          decoration: BoxDecoration(
            color: isDarkMode 
                ? elevatedSurfaceDark.withOpacity(0.80)
                : Colors.white.withOpacity(0.85),
            borderRadius: cardRadius,
            border: Border.all(
              color: isDarkMode ? hairlineBorderDark : Colors.black.withOpacity(0.08),
              width: 0.5,
            ),
          ),
          padding: padding,
          child: child,
        ),
      ),
    );
  }
}
