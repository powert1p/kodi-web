import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import '../../app/colors.dart';

/// Renders text with inline math expressions.
/// Converts plain-text math notation to LaTeX and renders mixed text+math.
class MathText extends StatelessWidget {
  const MathText(this.text, {super.key, this.style});
  final String text;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final defaultStyle = style ??
        const TextStyle(fontSize: 17, height: 1.6, color: AppColors.textPrimary);

    final segments = _parse(text);

    if (segments.length == 1 && !segments[0].isMath) {
      return Text(text, style: defaultStyle);
    }

    // Use RichText approach with WidgetSpan for math
    return Text.rich(
      TextSpan(
        children: segments.map((s) {
          if (s.isMath) {
            return WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: Math.tex(
                s.content,
                textStyle: defaultStyle.copyWith(
                  fontSize: (defaultStyle.fontSize ?? 17) * 1.15,
                ),
                mathStyle: MathStyle.text,
              ),
            );
          }
          return TextSpan(text: s.content, style: defaultStyle);
        }).toList(),
      ),
    );
  }

  static List<_Segment> _parse(String text) {
    final result = <_Segment>[];
    final processed = _convertToLatex(text);
    final regex = RegExp(r'\$([^$]+)\$');
    var lastEnd = 0;

    for (final match in regex.allMatches(processed)) {
      if (match.start > lastEnd) {
        result.add(_Segment(processed.substring(lastEnd, match.start), isMath: false));
      }
      result.add(_Segment(match.group(1)!, isMath: true));
      lastEnd = match.end;
    }
    if (lastEnd < processed.length) {
      result.add(_Segment(processed.substring(lastEnd), isMath: false));
    }

    return result.isEmpty ? [_Segment(text, isMath: false)] : result;
  }

  static String _convertToLatex(String text) {
    var result = text;

    // Mixed numbers: "2 3/4" → "$2\frac{3}{4}$"
    result = result.replaceAllMapped(
      RegExp(r'(\d+)\s+(\d+)/(\d+)'),
      (m) => '\$${m[1]}\\frac{${m[2]}}{${m[3]}}\$',
    );

    // Simple fractions: "1/3" → "$\frac{1}{3}$"
    result = result.replaceAllMapped(
      RegExp(r'(?<!\d{2})(?<!\w)(\d{1,4})/(\d{1,4})(?!\w)(?!/\d)'),
      (m) => '\$\\frac{${m[1]}}{${m[2]}}\$',
    );

    // Powers: "x^2", "8^2"
    result = result.replaceAllMapped(
      RegExp(r'(\w+|\))\^(\d+|\{[^}]+\})'),
      (m) {
        final base = m[1]!;
        final exp = m[2]!;
        final expClean = exp.startsWith('{') ? exp : '{$exp}';
        return '\$$base^$expClean\$';
      },
    );

    // √25 → "$\sqrt{25}$"
    result = result.replaceAllMapped(
      RegExp(r'√(\d+)'),
      (m) => '\$\\sqrt{${m[1]}}\$',
    );

    // ⋅ → "$\cdot$"
    result = result.replaceAll('⋅', '\$\\cdot\$');

    return result;
  }
}

class _Segment {
  _Segment(this.content, {required this.isMath});
  final String content;
  final bool isMath;
}
