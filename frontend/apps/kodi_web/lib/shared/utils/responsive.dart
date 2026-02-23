import 'dart:math';
import 'package:flutter/widgets.dart';

const double _designWidth = 414; // iPhone Pro Max baseline

/// Responsive size — scales proportionally to screen width.
/// On 414px screens returns original value; on smaller screens scales down.
double rs(BuildContext context, double size) {
  final w = MediaQuery.of(context).size.width;
  final scale = min(1.0, w / _designWidth);
  return (size * scale).roundToDouble();
}

/// Responsive padding — stepped reduction for small screens.
double rp(BuildContext context, double padding) {
  final w = MediaQuery.of(context).size.width;
  if (w < 360) return padding * 0.65;
  if (w < 390) return padding * 0.8;
  return padding;
}

/// Quick check for narrow screens (iPhone SE, Mini, etc.)
bool isSmallScreen(BuildContext context) =>
    MediaQuery.of(context).size.width < 375;
