import 'package:flutter/material.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../app/colors.dart';

/// Shows report bottom sheet and submits to API.
Future<void> showReportSheet(BuildContext context, NisApiClient api, int problemId, {String? studentAnswer}) async {
  final l = AppLocalizations.of(context)!;
  final reason = await showModalBottomSheet<String>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => Padding(
      padding: const EdgeInsets.all(24),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(l.reportTitle,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        ListTile(
          leading: Icon(Icons.error_outline, color: AppColors.error),
          title: Text(l.reportErrorInProblem),
          onTap: () => Navigator.pop(context, 'error')),
        ListTile(
          leading: Icon(Icons.help_outline, color: AppColors.warning),
          title: Text(l.reportWrongAnswer),
          onTap: () => Navigator.pop(context, 'wrong_answer')),
        ListTile(
          leading: Icon(Icons.visibility_off, color: AppColors.textSecondary),
          title: Text(l.reportUnclear),
          onTap: () => Navigator.pop(context, 'unclear')),
      ])));
  if (reason == null) return;
  try {
    await api.post('/api/practice/report', {
      'problem_id': problemId,
      'reason': reason,
      if (studentAnswer != null && studentAnswer.isNotEmpty)
        'student_answer': studentAnswer,
    });
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.reportThanks)));
    }
  } catch (e, st) {
    debugPrint('[showReportSheet] $e\n$st');
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.reportFailed)));
    }
  }
}
