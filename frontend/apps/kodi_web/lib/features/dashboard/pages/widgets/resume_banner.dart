import 'package:flutter/material.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import '../../../../app/colors.dart';

class ResumeBanner extends StatelessWidget {
  const ResumeBanner({super.key, required this.onResume});
  final VoidCallback onResume;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.warningBgLight,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.orange.withValues(alpha: 0.4)),
      ),
      child: Row(children: [
        Container(
          width: 44, height: 44,
          decoration: BoxDecoration(
            color: AppColors.orange.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(12)),
          child: const Icon(Icons.pause_circle_filled_rounded,
            color: AppColors.orange, size: 24)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l.resumeBannerTitle,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14,
                  color: AppColors.textPrimary)),
              Text(l.resumeBannerSubtitle,
                style: TextStyle(fontSize: 12, color: Colors.grey[600])),
            ],
          ),
        ),
        const SizedBox(width: 8),
        FilledButton(
          onPressed: onResume,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.orange,
            padding: const EdgeInsets.symmetric(horizontal: 16)),
          child: Text(l.resumeBannerBtn,
            style: const TextStyle(fontWeight: FontWeight.w600))),
      ]),
    );
  }
}
