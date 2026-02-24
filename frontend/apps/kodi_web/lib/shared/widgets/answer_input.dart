import 'package:flutter/material.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import '../../app/colors.dart';
import '../utils/responsive.dart';

/// Shared answer input card used by Practice, Diagnostic, and Exam pages.
class AnswerInput extends StatelessWidget {
  const AnswerInput({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.onSubmit,
    this.onSkip,
    this.onReport,
    this.accentColor = AppColors.primary,
    this.showHints = true,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final VoidCallback onSubmit;
  final VoidCallback? onSkip;
  final VoidCallback? onReport;
  final Color accentColor;
  final bool showHints;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(
          color: Colors.black.withValues(alpha: 0.04),
          blurRadius: 6, offset: const Offset(0, 2))]),
      padding: EdgeInsets.all(rp(context, 16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (showHints)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              Text(l.yourAnswer,
                style: TextStyle(fontSize: rs(context, 13), fontWeight: FontWeight.w600,
                  color: Colors.grey[600])),
              const Spacer(),
              Text(l.enterToAnswer,
                style: TextStyle(fontSize: rs(context, 11), color: Colors.grey[400])),
            ]),
          ),
        TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            hintText: l.answerHint,
            filled: true,
            fillColor: AppColors.surface,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: AppColors.border)),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: AppColors.border)),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: accentColor, width: 2)),
            contentPadding: EdgeInsets.symmetric(horizontal: rp(context, 16), vertical: 14),
            suffixIcon: IconButton(
              icon: Icon(Icons.send_rounded, color: accentColor),
              onPressed: onSubmit)),
          style: TextStyle(fontSize: rs(context, 16)),
          onSubmitted: (_) => onSubmit()),
        const SizedBox(height: 12),
        LayoutBuilder(builder: (context, constraints) {
          final narrow = constraints.maxWidth < 320;
          final btnHeight = rs(context, 48);
          final children = <Widget>[
            Expanded(child: FilledButton(
              onPressed: onSubmit,
              style: FilledButton.styleFrom(
                minimumSize: Size(0, btnHeight),
                backgroundColor: accentColor),
              child: Text(l.submitAnswer,
                style: TextStyle(fontSize: rs(context, 15), fontWeight: FontWeight.w600)))),
            if (onSkip != null) ...[
              SizedBox(width: narrow ? 6 : 10),
              SizedBox(height: btnHeight, child: OutlinedButton(
                onPressed: onSkip,
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: AppColors.border),
                  padding: EdgeInsets.symmetric(horizontal: rp(context, 16))),
                child: Text(l.skipBtn,
                  style: TextStyle(color: AppColors.textSecondary, fontSize: rs(context, 14))))),
            ],
            if (onReport != null) ...[
              const SizedBox(width: 6),
              SizedBox(height: btnHeight, child: IconButton(
                onPressed: onReport,
                icon: Icon(Icons.flag_outlined, color: AppColors.borderLight, size: rs(context, 20)),
                tooltip: l.reportTooltip)),
            ],
          ];
          return Row(children: children);
        }),
      ]));
  }
}
