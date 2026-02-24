import 'package:flutter/widgets.dart';
import 'package:kodi_web/l10n/app_localizations.dart';

/// Maps BLoC error codes to localized strings.
String localizeError(BuildContext context, String code) {
  final l = AppLocalizations.of(context)!;
  return switch (code) {
    'authTelegramError' => l.authTelegramError,
    'authProfileError' => l.authProfileError,
    'practiceAnswerError' => l.practiceAnswerError,
    'practiceProblemError' => l.practiceProblemError,
    'diagnosticResumeError' => l.diagnosticResumeError,
    'diagnosticStartError' => l.diagnosticStartError,
    'diagnosticAnswerError' => l.diagnosticAnswerError,
    'diagnosticQuestionError' => l.diagnosticQuestionError,
    'diagnosticFinishError' => l.diagnosticFinishError,
    'dashboardLoadError' => l.dashboardLoadError,
    'examStartError' => l.examStartError,
    'examAnswerError' => l.examAnswerError,
    _ => code,
  };
}
