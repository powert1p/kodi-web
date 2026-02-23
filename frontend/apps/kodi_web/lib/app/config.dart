class AppConfig {
  // Change via --dart-define for different environments
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String telegramBotName = String.fromEnvironment(
    'TG_BOT_NAME',
    defaultValue: 'nis_math_test_bot',
  );
}
