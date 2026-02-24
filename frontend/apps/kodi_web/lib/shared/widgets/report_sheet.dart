import 'package:flutter/material.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../app/colors.dart';

/// Shows report bottom sheet and submits to API.
Future<void> showReportSheet(BuildContext context, NisApiClient api, int problemId) async {
  final reason = await showModalBottomSheet<String>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => Padding(
      padding: const EdgeInsets.all(24),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Что не так?',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        ListTile(
          leading: Icon(Icons.error_outline, color: AppColors.error),
          title: const Text('Ошибка в условии'),
          onTap: () => Navigator.pop(context, 'error')),
        ListTile(
          leading: Icon(Icons.help_outline, color: AppColors.warning),
          title: const Text('Неправильный ответ'),
          onTap: () => Navigator.pop(context, 'wrong_answer')),
        ListTile(
          leading: Icon(Icons.visibility_off, color: AppColors.textSecondary),
          title: const Text('Непонятное условие'),
          onTap: () => Navigator.pop(context, 'unclear')),
      ])));
  if (reason == null) return;
  try {
    await api.post('/api/practice/report', {
      'problem_id': problemId,
      'reason': reason,
    });
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Спасибо! Мы проверим.')));
    }
  } catch (e, st) {
    debugPrint('[showReportSheet] $e\n$st');
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось отправить. Попробуйте позже.')));
    }
  }
}
