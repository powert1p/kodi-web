import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_kk.dart';
import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('kk'),
    Locale('ru')
  ];

  /// No description provided for @appTitle.
  ///
  /// In ru, this message translates to:
  /// **'NIS Math'**
  String get appTitle;

  /// No description provided for @tagArithmetic.
  ///
  /// In ru, this message translates to:
  /// **'Арифметика'**
  String get tagArithmetic;

  /// No description provided for @tagFractions.
  ///
  /// In ru, this message translates to:
  /// **'Дроби'**
  String get tagFractions;

  /// No description provided for @tagDecimals.
  ///
  /// In ru, this message translates to:
  /// **'Десятичные дроби'**
  String get tagDecimals;

  /// No description provided for @tagDecimalsShort.
  ///
  /// In ru, this message translates to:
  /// **'Десятичные'**
  String get tagDecimalsShort;

  /// No description provided for @tagDivisibility.
  ///
  /// In ru, this message translates to:
  /// **'Делимость'**
  String get tagDivisibility;

  /// No description provided for @tagEquations.
  ///
  /// In ru, this message translates to:
  /// **'Уравнения'**
  String get tagEquations;

  /// No description provided for @tagGeometry.
  ///
  /// In ru, this message translates to:
  /// **'Геометрия'**
  String get tagGeometry;

  /// No description provided for @tagAlgebra.
  ///
  /// In ru, this message translates to:
  /// **'Алгебра'**
  String get tagAlgebra;

  /// No description provided for @tagWordProblems.
  ///
  /// In ru, this message translates to:
  /// **'Текстовые задачи'**
  String get tagWordProblems;

  /// No description provided for @tagWordProblemsShort.
  ///
  /// In ru, this message translates to:
  /// **'Текст. задачи'**
  String get tagWordProblemsShort;

  /// No description provided for @tagProportion.
  ///
  /// In ru, this message translates to:
  /// **'Пропорции'**
  String get tagProportion;

  /// No description provided for @tagPercent.
  ///
  /// In ru, this message translates to:
  /// **'Проценты'**
  String get tagPercent;

  /// No description provided for @tagRatios.
  ///
  /// In ru, this message translates to:
  /// **'Пропорции и проценты'**
  String get tagRatios;

  /// No description provided for @tagNumbers.
  ///
  /// In ru, this message translates to:
  /// **'Числа'**
  String get tagNumbers;

  /// No description provided for @tagNumberTheory.
  ///
  /// In ru, this message translates to:
  /// **'Теория чисел'**
  String get tagNumberTheory;

  /// No description provided for @tagConversion.
  ///
  /// In ru, this message translates to:
  /// **'Единицы измерения'**
  String get tagConversion;

  /// No description provided for @tagConversionShort.
  ///
  /// In ru, this message translates to:
  /// **'Ед. измерения'**
  String get tagConversionShort;

  /// No description provided for @tagMeasurement.
  ///
  /// In ru, this message translates to:
  /// **'Единицы измерения'**
  String get tagMeasurement;

  /// No description provided for @tagData.
  ///
  /// In ru, this message translates to:
  /// **'Данные'**
  String get tagData;

  /// No description provided for @tagDataAnalysis.
  ///
  /// In ru, this message translates to:
  /// **'Анализ данных'**
  String get tagDataAnalysis;

  /// No description provided for @tagCombinatorics.
  ///
  /// In ru, this message translates to:
  /// **'Комбинаторика'**
  String get tagCombinatorics;

  /// No description provided for @tagProbability.
  ///
  /// In ru, this message translates to:
  /// **'Вероятность'**
  String get tagProbability;

  /// No description provided for @tagStatistics.
  ///
  /// In ru, this message translates to:
  /// **'Статистика'**
  String get tagStatistics;

  /// No description provided for @tagModulus.
  ///
  /// In ru, this message translates to:
  /// **'Модуль числа'**
  String get tagModulus;

  /// No description provided for @tagSequences.
  ///
  /// In ru, this message translates to:
  /// **'Последовательности'**
  String get tagSequences;

  /// No description provided for @tagSets.
  ///
  /// In ru, this message translates to:
  /// **'Множества'**
  String get tagSets;

  /// No description provided for @tagNegative.
  ///
  /// In ru, this message translates to:
  /// **'Отрицательные числа'**
  String get tagNegative;

  /// No description provided for @tagRounding.
  ///
  /// In ru, this message translates to:
  /// **'Округление'**
  String get tagRounding;

  /// No description provided for @tagLogic.
  ///
  /// In ru, this message translates to:
  /// **'Логика'**
  String get tagLogic;

  /// No description provided for @onboardingHello.
  ///
  /// In ru, this message translates to:
  /// **'Привет, {name}! 👋'**
  String onboardingHello(String name);

  /// No description provided for @onboardingWelcome.
  ///
  /// In ru, this message translates to:
  /// **'Добро пожаловать в NIS Math!\nЗдесь ты подготовишься к экзамену по математике в НИШ.'**
  String get onboardingWelcome;

  /// No description provided for @onboardingStep1Title.
  ///
  /// In ru, this message translates to:
  /// **'Пройди диагностику'**
  String get onboardingStep1Title;

  /// No description provided for @onboardingStep1Subtitle.
  ///
  /// In ru, this message translates to:
  /// **'5-10 минут · система определит твой уровень'**
  String get onboardingStep1Subtitle;

  /// No description provided for @onboardingStep2Title.
  ///
  /// In ru, this message translates to:
  /// **'Узнай свои пробелы'**
  String get onboardingStep2Title;

  /// No description provided for @onboardingStep2Subtitle.
  ///
  /// In ru, this message translates to:
  /// **'AI покажет где у тебя слабые места'**
  String get onboardingStep2Subtitle;

  /// No description provided for @onboardingStep3Title.
  ///
  /// In ru, this message translates to:
  /// **'Тренируйся по темам'**
  String get onboardingStep3Title;

  /// No description provided for @onboardingStep3Subtitle.
  ///
  /// In ru, this message translates to:
  /// **'2525 задач с решениями и картинками'**
  String get onboardingStep3Subtitle;

  /// No description provided for @startDiagnostic.
  ///
  /// In ru, this message translates to:
  /// **'Начать диагностику'**
  String get startDiagnostic;

  /// No description provided for @examWithTimer.
  ///
  /// In ru, this message translates to:
  /// **'Экзамен с таймером'**
  String get examWithTimer;

  /// No description provided for @orJustSolve.
  ///
  /// In ru, this message translates to:
  /// **'Или просто порешать задачи →'**
  String get orJustSolve;

  /// No description provided for @loginSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Подготовка к поступлению в НИШ'**
  String get loginSubtitle;

  /// No description provided for @loginViaTelegram.
  ///
  /// In ru, this message translates to:
  /// **'Войти через Telegram'**
  String get loginViaTelegram;

  /// No description provided for @loginOr.
  ///
  /// In ru, this message translates to:
  /// **'или'**
  String get loginOr;

  /// No description provided for @loginFooter.
  ///
  /// In ru, this message translates to:
  /// **'2525 задач · 118 тем · БКТ-алгоритм'**
  String get loginFooter;

  /// No description provided for @phoneLabel.
  ///
  /// In ru, this message translates to:
  /// **'Номер телефона'**
  String get phoneLabel;

  /// No description provided for @phoneHint.
  ///
  /// In ru, this message translates to:
  /// **'+7 777 123 4567'**
  String get phoneHint;

  /// No description provided for @phoneContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get phoneContinue;

  /// No description provided for @phoneEnterNumber.
  ///
  /// In ru, this message translates to:
  /// **'Введите номер телефона'**
  String get phoneEnterNumber;

  /// No description provided for @phoneNewStudent.
  ///
  /// In ru, this message translates to:
  /// **'Новый ученик! Заполни имя и придумай PIN'**
  String get phoneNewStudent;

  /// No description provided for @phoneFoundNumber.
  ///
  /// In ru, this message translates to:
  /// **'Номер найден! Введи свой PIN'**
  String get phoneFoundNumber;

  /// No description provided for @phoneName.
  ///
  /// In ru, this message translates to:
  /// **'Имя'**
  String get phoneName;

  /// No description provided for @phoneNameHint.
  ///
  /// In ru, this message translates to:
  /// **'Как тебя зовут?'**
  String get phoneNameHint;

  /// No description provided for @phoneCreatePin.
  ///
  /// In ru, this message translates to:
  /// **'Придумай PIN (4 цифры)'**
  String get phoneCreatePin;

  /// No description provided for @phonePinCode.
  ///
  /// In ru, this message translates to:
  /// **'PIN-код'**
  String get phonePinCode;

  /// No description provided for @phonePinHint.
  ///
  /// In ru, this message translates to:
  /// **'••••'**
  String get phonePinHint;

  /// No description provided for @phoneRegister.
  ///
  /// In ru, this message translates to:
  /// **'Зарегистрироваться'**
  String get phoneRegister;

  /// No description provided for @phoneLogin.
  ///
  /// In ru, this message translates to:
  /// **'Войти'**
  String get phoneLogin;

  /// No description provided for @phoneChangeNumber.
  ///
  /// In ru, this message translates to:
  /// **'Изменить номер'**
  String get phoneChangeNumber;

  /// No description provided for @phonePin4Digits.
  ///
  /// In ru, this message translates to:
  /// **'PIN — 4 цифры'**
  String get phonePin4Digits;

  /// No description provided for @phoneEnterName.
  ///
  /// In ru, this message translates to:
  /// **'Введите имя'**
  String get phoneEnterName;

  /// No description provided for @phoneCheckError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось проверить номер. Попробуйте ещё раз.'**
  String get phoneCheckError;

  /// No description provided for @phoneLoginError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось войти. Попробуйте ещё раз.'**
  String get phoneLoginError;

  /// No description provided for @practiceTitle.
  ///
  /// In ru, this message translates to:
  /// **'Практика'**
  String get practiceTitle;

  /// No description provided for @sessionStats.
  ///
  /// In ru, this message translates to:
  /// **'Статистика сессии'**
  String get sessionStats;

  /// No description provided for @solved.
  ///
  /// In ru, this message translates to:
  /// **'Решено'**
  String get solved;

  /// No description provided for @correct.
  ///
  /// In ru, this message translates to:
  /// **'Правильно'**
  String get correct;

  /// No description provided for @accuracy.
  ///
  /// In ru, this message translates to:
  /// **'Точность'**
  String get accuracy;

  /// No description provided for @avgTime.
  ///
  /// In ru, this message translates to:
  /// **'Ср. время'**
  String get avgTime;

  /// No description provided for @maxCombo.
  ///
  /// In ru, this message translates to:
  /// **'Макс комбо'**
  String get maxCombo;

  /// No description provided for @total.
  ///
  /// In ru, this message translates to:
  /// **'Всего'**
  String get total;

  /// No description provided for @continueBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get continueBtn;

  /// No description provided for @finishPracticeTitle.
  ///
  /// In ru, this message translates to:
  /// **'Завершить практику?'**
  String get finishPracticeTitle;

  /// No description provided for @finishPracticeContent.
  ///
  /// In ru, this message translates to:
  /// **'Решено задач: {count}, правильно: {correct}.'**
  String finishPracticeContent(int count, int correct);

  /// No description provided for @exitBtn.
  ///
  /// In ru, this message translates to:
  /// **'Выйти'**
  String get exitBtn;

  /// No description provided for @statisticsTooltip.
  ///
  /// In ru, this message translates to:
  /// **'Статистика'**
  String get statisticsTooltip;

  /// No description provided for @allSolved.
  ///
  /// In ru, this message translates to:
  /// **'Все задачи решены! 🎉'**
  String get allSolved;

  /// No description provided for @tryAnotherTopic.
  ///
  /// In ru, this message translates to:
  /// **'Попробуй другую тему'**
  String get tryAnotherTopic;

  /// No description provided for @goHome.
  ///
  /// In ru, this message translates to:
  /// **'На главную'**
  String get goHome;

  /// No description provided for @nextBtn.
  ///
  /// In ru, this message translates to:
  /// **'Следующая'**
  String get nextBtn;

  /// No description provided for @arrowOrSpace.
  ///
  /// In ru, this message translates to:
  /// **'→ или пробел'**
  String get arrowOrSpace;

  /// No description provided for @comboStreak.
  ///
  /// In ru, this message translates to:
  /// **'{count} подряд!'**
  String comboStreak(int count);

  /// No description provided for @diagnosticTitle.
  ///
  /// In ru, this message translates to:
  /// **'Диагностика'**
  String get diagnosticTitle;

  /// No description provided for @leaveDiagnosticTitle.
  ///
  /// In ru, this message translates to:
  /// **'Покинуть диагностику?'**
  String get leaveDiagnosticTitle;

  /// No description provided for @leaveDiagnosticContent.
  ///
  /// In ru, this message translates to:
  /// **'Прогресс будет сохранён — вы сможете продолжить позже.'**
  String get leaveDiagnosticContent;

  /// No description provided for @stayBtn.
  ///
  /// In ru, this message translates to:
  /// **'Остаться'**
  String get stayBtn;

  /// No description provided for @diagnosticKnowledge.
  ///
  /// In ru, this message translates to:
  /// **'Диагностика знаний'**
  String get diagnosticKnowledge;

  /// No description provided for @diagnosticDescription.
  ///
  /// In ru, this message translates to:
  /// **'15 тем — адаптивный алгоритм подберёт задачи под тебя.'**
  String get diagnosticDescription;

  /// No description provided for @diagnosticExamMode.
  ///
  /// In ru, this message translates to:
  /// **'Готовлюсь к экзамену'**
  String get diagnosticExamMode;

  /// No description provided for @diagnosticExamSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'15 тем · 10-15 минут'**
  String get diagnosticExamSubtitle;

  /// No description provided for @diagnosticExamDescription.
  ///
  /// In ru, this message translates to:
  /// **'Сложные темы первыми — проверь готовность'**
  String get diagnosticExamDescription;

  /// No description provided for @diagnosticGapsMode.
  ///
  /// In ru, this message translates to:
  /// **'Проверяю пробелы'**
  String get diagnosticGapsMode;

  /// No description provided for @diagnosticGapsSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'15 тем · 10-15 минут'**
  String get diagnosticGapsSubtitle;

  /// No description provided for @diagnosticGapsDescription.
  ///
  /// In ru, this message translates to:
  /// **'С базовых тем вверх — найди слабые места'**
  String get diagnosticGapsDescription;

  /// No description provided for @startBtn.
  ///
  /// In ru, this message translates to:
  /// **'Начать'**
  String get startBtn;

  /// No description provided for @topicNofM.
  ///
  /// In ru, this message translates to:
  /// **'Тема {current} из {max}'**
  String topicNofM(int current, int max);

  /// No description provided for @nCorrect.
  ///
  /// In ru, this message translates to:
  /// **'{count} правильно'**
  String nCorrect(int count);

  /// No description provided for @finishBtn.
  ///
  /// In ru, this message translates to:
  /// **'Завершить'**
  String get finishBtn;

  /// No description provided for @diagnosticComplete.
  ///
  /// In ru, this message translates to:
  /// **'Диагностика завершена!'**
  String get diagnosticComplete;

  /// No description provided for @mastered.
  ///
  /// In ru, this message translates to:
  /// **'Освоено'**
  String get mastered;

  /// No description provided for @gaps.
  ///
  /// In ru, this message translates to:
  /// **'Пробелы'**
  String get gaps;

  /// No description provided for @masteredTopics.
  ///
  /// In ru, this message translates to:
  /// **'Освоенные темы'**
  String get masteredTopics;

  /// No description provided for @weakTopics.
  ///
  /// In ru, this message translates to:
  /// **'Слабые темы'**
  String get weakTopics;

  /// No description provided for @somethingWentWrong.
  ///
  /// In ru, this message translates to:
  /// **'Что-то пошло не так'**
  String get somethingWentWrong;

  /// No description provided for @tryAgain.
  ///
  /// In ru, this message translates to:
  /// **'Попробовать снова'**
  String get tryAgain;

  /// No description provided for @unfinishedDiagnostic.
  ///
  /// In ru, this message translates to:
  /// **'Незавершённая диагностика'**
  String get unfinishedDiagnostic;

  /// No description provided for @unfinishedDiagnosticInfo.
  ///
  /// In ru, this message translates to:
  /// **'{mode} — {tested} из {max} тем · {questions} вопросов'**
  String unfinishedDiagnosticInfo(
      String mode, int tested, int max, int questions);

  /// No description provided for @resumeBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get resumeBtn;

  /// No description provided for @startOver.
  ///
  /// In ru, this message translates to:
  /// **'Начать заново'**
  String get startOver;

  /// No description provided for @examPreparation.
  ///
  /// In ru, this message translates to:
  /// **'Подготовка к экзамену'**
  String get examPreparation;

  /// No description provided for @gapsCheck.
  ///
  /// In ru, this message translates to:
  /// **'Проверка пробелов'**
  String get gapsCheck;

  /// No description provided for @examTitle.
  ///
  /// In ru, this message translates to:
  /// **'Экзамен'**
  String get examTitle;

  /// No description provided for @leaveExamTitle.
  ///
  /// In ru, this message translates to:
  /// **'Покинуть экзамен?'**
  String get leaveExamTitle;

  /// No description provided for @leaveExamContent.
  ///
  /// In ru, this message translates to:
  /// **'Таймер идёт! Если выйдешь, прогресс будет потерян.'**
  String get leaveExamContent;

  /// No description provided for @examSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Реши задачи на время — как на настоящем НИШ'**
  String get examSubtitle;

  /// No description provided for @examSettings.
  ///
  /// In ru, this message translates to:
  /// **'Настройки'**
  String get examSettings;

  /// No description provided for @examProblems.
  ///
  /// In ru, this message translates to:
  /// **'Задач:'**
  String get examProblems;

  /// No description provided for @examTime.
  ///
  /// In ru, this message translates to:
  /// **'Время:'**
  String get examTime;

  /// No description provided for @examTimeMinutes.
  ///
  /// In ru, this message translates to:
  /// **'{minutes} мин'**
  String examTimeMinutes(int minutes);

  /// No description provided for @startExam.
  ///
  /// In ru, this message translates to:
  /// **'Начать экзамен'**
  String get startExam;

  /// No description provided for @problemNofM.
  ///
  /// In ru, this message translates to:
  /// **'Задача {current} из {total}'**
  String problemNofM(int current, int total);

  /// No description provided for @excellent.
  ///
  /// In ru, this message translates to:
  /// **'Отлично!'**
  String get excellent;

  /// No description provided for @canDoBetter.
  ///
  /// In ru, this message translates to:
  /// **'Можно лучше!'**
  String get canDoBetter;

  /// No description provided for @timeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Время: {time}'**
  String timeLabel(String time);

  /// No description provided for @result.
  ///
  /// In ru, this message translates to:
  /// **'Результат'**
  String get result;

  /// No description provided for @skipped.
  ///
  /// In ru, this message translates to:
  /// **'Пропущено'**
  String get skipped;

  /// No description provided for @oneMoreTime.
  ///
  /// In ru, this message translates to:
  /// **'Ещё раз'**
  String get oneMoreTime;

  /// No description provided for @backBtn.
  ///
  /// In ru, this message translates to:
  /// **'Назад'**
  String get backBtn;

  /// No description provided for @graphTitle.
  ///
  /// In ru, this message translates to:
  /// **'Граф знаний'**
  String get graphTitle;

  /// No description provided for @graphBtn.
  ///
  /// In ru, this message translates to:
  /// **'Граф'**
  String get graphBtn;

  /// No description provided for @logoutTooltip.
  ///
  /// In ru, this message translates to:
  /// **'Выйти'**
  String get logoutTooltip;

  /// No description provided for @legendMastered.
  ///
  /// In ru, this message translates to:
  /// **'Освоено'**
  String get legendMastered;

  /// No description provided for @legendPartial.
  ///
  /// In ru, this message translates to:
  /// **'Частично'**
  String get legendPartial;

  /// No description provided for @legendFailed.
  ///
  /// In ru, this message translates to:
  /// **'Провалено'**
  String get legendFailed;

  /// No description provided for @legendUntested.
  ///
  /// In ru, this message translates to:
  /// **'Не проверено'**
  String get legendUntested;

  /// No description provided for @heroHello.
  ///
  /// In ru, this message translates to:
  /// **'Привет, {name}! 👋'**
  String heroHello(String name);

  /// No description provided for @yourProgress.
  ///
  /// In ru, this message translates to:
  /// **'Твой прогресс'**
  String get yourProgress;

  /// No description provided for @topicsMastered.
  ///
  /// In ru, this message translates to:
  /// **'{mastered} из {total} тем освоено'**
  String topicsMastered(int mastered, int total);

  /// No description provided for @streakDays.
  ///
  /// In ru, this message translates to:
  /// **'{count} {day} подряд'**
  String streakDays(int count, String day);

  /// No description provided for @day1.
  ///
  /// In ru, this message translates to:
  /// **'день'**
  String get day1;

  /// No description provided for @day2to4.
  ///
  /// In ru, this message translates to:
  /// **'дня'**
  String get day2to4;

  /// No description provided for @day5plus.
  ///
  /// In ru, this message translates to:
  /// **'дней'**
  String get day5plus;

  /// No description provided for @statMastered.
  ///
  /// In ru, this message translates to:
  /// **'Освоено'**
  String get statMastered;

  /// No description provided for @statSolved.
  ///
  /// In ru, this message translates to:
  /// **'Решено'**
  String get statSolved;

  /// No description provided for @statAccuracy.
  ///
  /// In ru, this message translates to:
  /// **'Точность'**
  String get statAccuracy;

  /// No description provided for @statAvgTime.
  ///
  /// In ru, this message translates to:
  /// **'Ср. время'**
  String get statAvgTime;

  /// No description provided for @dashboardDiagnostic.
  ///
  /// In ru, this message translates to:
  /// **'Диагностика'**
  String get dashboardDiagnostic;

  /// No description provided for @dashboardPractice.
  ///
  /// In ru, this message translates to:
  /// **'Практика'**
  String get dashboardPractice;

  /// No description provided for @dashboardLeaderboard.
  ///
  /// In ru, this message translates to:
  /// **'Рейтинг'**
  String get dashboardLeaderboard;

  /// No description provided for @sectionsHeader.
  ///
  /// In ru, this message translates to:
  /// **'РАЗДЕЛЫ'**
  String get sectionsHeader;

  /// No description provided for @tabTopics.
  ///
  /// In ru, this message translates to:
  /// **'Темы'**
  String get tabTopics;

  /// No description provided for @tabProblems.
  ///
  /// In ru, this message translates to:
  /// **'Задачи'**
  String get tabProblems;

  /// No description provided for @sectionTestedOfTotal.
  ///
  /// In ru, this message translates to:
  /// **'{tested} из {total} проверено'**
  String sectionTestedOfTotal(int tested, int total);

  /// No description provided for @sectionTopicsCount.
  ///
  /// In ru, this message translates to:
  /// **'{count} тем'**
  String sectionTopicsCount(int count);

  /// No description provided for @trainSection.
  ///
  /// In ru, this message translates to:
  /// **'Тренировать: {name}'**
  String trainSection(String name);

  /// No description provided for @tapToPractice.
  ///
  /// In ru, this message translates to:
  /// **'Нажми чтобы практиковать'**
  String get tapToPractice;

  /// No description provided for @startLearning.
  ///
  /// In ru, this message translates to:
  /// **'Начать изучение'**
  String get startLearning;

  /// No description provided for @noSolvedProblems.
  ///
  /// In ru, this message translates to:
  /// **'Нет решённых задач'**
  String get noSolvedProblems;

  /// No description provided for @notSolvedYet.
  ///
  /// In ru, this message translates to:
  /// **'Ещё не решал'**
  String get notSolvedYet;

  /// No description provided for @resumeBannerTitle.
  ///
  /// In ru, this message translates to:
  /// **'Незавершённая диагностика'**
  String get resumeBannerTitle;

  /// No description provided for @resumeBannerSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Продолжи с того места, где остановился'**
  String get resumeBannerSubtitle;

  /// No description provided for @resumeBannerBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get resumeBannerBtn;

  /// No description provided for @retryBtn.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get retryBtn;

  /// No description provided for @leaderboardTitle.
  ///
  /// In ru, this message translates to:
  /// **'🏆 Лидерборд'**
  String get leaderboardTitle;

  /// No description provided for @sortByQuantity.
  ///
  /// In ru, this message translates to:
  /// **'По количеству'**
  String get sortByQuantity;

  /// No description provided for @sortByAccuracy.
  ///
  /// In ru, this message translates to:
  /// **'По точности'**
  String get sortByAccuracy;

  /// No description provided for @sortByProgress.
  ///
  /// In ru, this message translates to:
  /// **'По прогрессу'**
  String get sortByProgress;

  /// No description provided for @itsYou.
  ///
  /// In ru, this message translates to:
  /// **'Это вы'**
  String get itsYou;

  /// No description provided for @reportTitle.
  ///
  /// In ru, this message translates to:
  /// **'Что не так?'**
  String get reportTitle;

  /// No description provided for @reportErrorInProblem.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка в условии'**
  String get reportErrorInProblem;

  /// No description provided for @reportWrongAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Неправильный ответ'**
  String get reportWrongAnswer;

  /// No description provided for @reportUnclear.
  ///
  /// In ru, this message translates to:
  /// **'Непонятное условие'**
  String get reportUnclear;

  /// No description provided for @reportThanks.
  ///
  /// In ru, this message translates to:
  /// **'Спасибо! Мы проверим.'**
  String get reportThanks;

  /// No description provided for @reportFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось отправить. Попробуйте позже.'**
  String get reportFailed;

  /// No description provided for @reportTooltip.
  ///
  /// In ru, this message translates to:
  /// **'Пожаловаться'**
  String get reportTooltip;

  /// No description provided for @correctAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Правильно! 🎉'**
  String get correctAnswer;

  /// No description provided for @incorrectAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Неправильно'**
  String get incorrectAnswer;

  /// No description provided for @masteredBadge.
  ///
  /// In ru, this message translates to:
  /// **'Освоено'**
  String get masteredBadge;

  /// No description provided for @answerLabel.
  ///
  /// In ru, this message translates to:
  /// **'Ответ: '**
  String get answerLabel;

  /// No description provided for @solutionLabel.
  ///
  /// In ru, this message translates to:
  /// **'Решение:'**
  String get solutionLabel;

  /// No description provided for @masteryLabel.
  ///
  /// In ru, this message translates to:
  /// **'Освоение: '**
  String get masteryLabel;

  /// No description provided for @yourAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Ваш ответ'**
  String get yourAnswer;

  /// No description provided for @enterToAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Enter — ответить'**
  String get enterToAnswer;

  /// No description provided for @answerHint.
  ///
  /// In ru, this message translates to:
  /// **'Введите ответ...'**
  String get answerHint;

  /// No description provided for @submitAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Ответить'**
  String get submitAnswer;

  /// No description provided for @skipBtn.
  ///
  /// In ru, this message translates to:
  /// **'Пропустить'**
  String get skipBtn;

  /// No description provided for @page404.
  ///
  /// In ru, this message translates to:
  /// **'404'**
  String get page404;

  /// No description provided for @authTelegramError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось войти через Telegram. Попробуйте ещё раз.'**
  String get authTelegramError;

  /// No description provided for @authProfileError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось загрузить профиль. Попробуйте ещё раз.'**
  String get authProfileError;

  /// No description provided for @practiceAnswerError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось отправить ответ'**
  String get practiceAnswerError;

  /// No description provided for @practiceProblemError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось загрузить задачу'**
  String get practiceProblemError;

  /// No description provided for @diagnosticResumeError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось продолжить диагностику'**
  String get diagnosticResumeError;

  /// No description provided for @diagnosticStartError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось начать диагностику'**
  String get diagnosticStartError;

  /// No description provided for @diagnosticAnswerError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось отправить ответ'**
  String get diagnosticAnswerError;

  /// No description provided for @diagnosticQuestionError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось загрузить вопрос'**
  String get diagnosticQuestionError;

  /// No description provided for @diagnosticFinishError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось завершить диагностику'**
  String get diagnosticFinishError;

  /// No description provided for @dashboardLoadError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось загрузить данные'**
  String get dashboardLoadError;

  /// No description provided for @examStartError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось запустить экзамен'**
  String get examStartError;

  /// No description provided for @examAnswerError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось отправить ответ'**
  String get examAnswerError;

  /// No description provided for @leaderboardDefaultName.
  ///
  /// In ru, this message translates to:
  /// **'Ученик'**
  String get leaderboardDefaultName;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['kk', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'kk':
      return AppLocalizationsKk();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
