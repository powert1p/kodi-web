// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appTitle => 'NIS Math';

  @override
  String get tagArithmetic => 'Арифметика';

  @override
  String get tagFractions => 'Дроби';

  @override
  String get tagDecimals => 'Десятичные дроби';

  @override
  String get tagDecimalsShort => 'Десятичные';

  @override
  String get tagDivisibility => 'Делимость';

  @override
  String get tagEquations => 'Уравнения';

  @override
  String get tagGeometry => 'Геометрия';

  @override
  String get tagAlgebra => 'Алгебра';

  @override
  String get tagWordProblems => 'Текстовые задачи';

  @override
  String get tagWordProblemsShort => 'Текст. задачи';

  @override
  String get tagProportion => 'Пропорции';

  @override
  String get tagPercent => 'Проценты';

  @override
  String get tagRatios => 'Пропорции и проценты';

  @override
  String get tagNumbers => 'Числа';

  @override
  String get tagNumberTheory => 'Теория чисел';

  @override
  String get tagConversion => 'Единицы измерения';

  @override
  String get tagConversionShort => 'Ед. измерения';

  @override
  String get tagMeasurement => 'Единицы измерения';

  @override
  String get tagData => 'Данные';

  @override
  String get tagDataAnalysis => 'Анализ данных';

  @override
  String get tagCombinatorics => 'Комбинаторика';

  @override
  String get tagProbability => 'Вероятность';

  @override
  String get tagStatistics => 'Статистика';

  @override
  String get tagModulus => 'Модуль числа';

  @override
  String get tagSequences => 'Последовательности';

  @override
  String get tagSets => 'Множества';

  @override
  String get tagNegative => 'Отрицательные числа';

  @override
  String get tagRounding => 'Округление';

  @override
  String get tagLogic => 'Логика';

  @override
  String onboardingHello(String name) {
    return 'Привет, $name! 👋';
  }

  @override
  String get onboardingWelcome =>
      'Добро пожаловать в NIS Math!\nЗдесь ты подготовишься к экзамену по математике в НИШ.';

  @override
  String get onboardingStep1Title => 'Пройди диагностику';

  @override
  String get onboardingStep1Subtitle =>
      '5-10 минут · система определит твой уровень';

  @override
  String get onboardingStep2Title => 'Узнай свои пробелы';

  @override
  String get onboardingStep2Subtitle => 'AI покажет где у тебя слабые места';

  @override
  String get onboardingStep3Title => 'Тренируйся по темам';

  @override
  String get onboardingStep3Subtitle => '2525 задач с решениями и картинками';

  @override
  String get startDiagnostic => 'Начать диагностику';

  @override
  String get examWithTimer => 'Экзамен с таймером';

  @override
  String get orJustSolve => 'Или просто порешать задачи →';

  @override
  String get loginSubtitle => 'Подготовка к поступлению в НИШ';

  @override
  String get loginViaTelegram => 'Войти через Telegram';

  @override
  String get loginOr => 'или';

  @override
  String get loginFooter => '2525 задач · 118 тем · БКТ-алгоритм';

  @override
  String get phoneLabel => 'Номер телефона';

  @override
  String get phoneHint => '+7 777 123 4567';

  @override
  String get phoneContinue => 'Продолжить';

  @override
  String get phoneEnterNumber => 'Введите номер телефона';

  @override
  String get phoneNewStudent => 'Новый ученик! Заполни имя и придумай PIN';

  @override
  String get phoneFoundNumber => 'Номер найден! Введи свой PIN';

  @override
  String get phoneName => 'Имя';

  @override
  String get phoneNameHint => 'Как тебя зовут?';

  @override
  String get phoneCreatePin => 'Придумай PIN (4 цифры)';

  @override
  String get phonePinCode => 'PIN-код';

  @override
  String get phonePinHint => '••••';

  @override
  String get phoneRegister => 'Зарегистрироваться';

  @override
  String get phoneLogin => 'Войти';

  @override
  String get phoneChangeNumber => 'Изменить номер';

  @override
  String get phonePin4Digits => 'PIN — 4 цифры';

  @override
  String get phoneEnterName => 'Введите имя';

  @override
  String get phoneCheckError =>
      'Не удалось проверить номер. Попробуйте ещё раз.';

  @override
  String get phoneLoginError => 'Не удалось войти. Попробуйте ещё раз.';

  @override
  String get practiceTitle => 'Практика';

  @override
  String get sessionStats => 'Статистика сессии';

  @override
  String get solved => 'Решено';

  @override
  String get correct => 'Правильно';

  @override
  String get accuracy => 'Точность';

  @override
  String get avgTime => 'Ср. время';

  @override
  String get maxCombo => 'Макс комбо';

  @override
  String get total => 'Всего';

  @override
  String get continueBtn => 'Продолжить';

  @override
  String get finishPracticeTitle => 'Завершить практику?';

  @override
  String finishPracticeContent(int count, int correct) {
    return 'Решено задач: $count, правильно: $correct.';
  }

  @override
  String get exitBtn => 'Выйти';

  @override
  String get statisticsTooltip => 'Статистика';

  @override
  String get allSolved => 'Все задачи решены! 🎉';

  @override
  String get tryAnotherTopic => 'Попробуй другую тему';

  @override
  String get goHome => 'На главную';

  @override
  String get nextBtn => 'Следующая';

  @override
  String get arrowOrSpace => '→ или пробел';

  @override
  String comboStreak(int count) {
    return '$count подряд!';
  }

  @override
  String get diagnosticTitle => 'Диагностика';

  @override
  String get leaveDiagnosticTitle => 'Покинуть диагностику?';

  @override
  String get leaveDiagnosticContent =>
      'Прогресс будет сохранён — вы сможете продолжить позже.';

  @override
  String get stayBtn => 'Остаться';

  @override
  String get diagnosticKnowledge => 'Диагностика знаний';

  @override
  String get diagnosticDescription =>
      '15 тем — адаптивный алгоритм подберёт задачи под тебя.';

  @override
  String get diagnosticExamMode => 'Готовлюсь к экзамену';

  @override
  String get diagnosticExamSubtitle => '15 тем · 10-15 минут';

  @override
  String get diagnosticExamDescription =>
      'Сложные темы первыми — проверь готовность';

  @override
  String get diagnosticGapsMode => 'Проверяю пробелы';

  @override
  String get diagnosticGapsSubtitle => '15 тем · 10-15 минут';

  @override
  String get diagnosticGapsDescription =>
      'С базовых тем вверх — найди слабые места';

  @override
  String get startBtn => 'Начать';

  @override
  String topicNofM(int current, int max) {
    return 'Тема $current из $max';
  }

  @override
  String nCorrect(int count) {
    return '$count правильно';
  }

  @override
  String get finishBtn => 'Завершить';

  @override
  String get diagnosticComplete => 'Диагностика завершена!';

  @override
  String get mastered => 'Освоено';

  @override
  String get gaps => 'Пробелы';

  @override
  String get masteredTopics => 'Освоенные темы';

  @override
  String get weakTopics => 'Слабые темы';

  @override
  String get somethingWentWrong => 'Что-то пошло не так';

  @override
  String get tryAgain => 'Попробовать снова';

  @override
  String get unfinishedDiagnostic => 'Незавершённая диагностика';

  @override
  String unfinishedDiagnosticInfo(
      String mode, int tested, int max, int questions) {
    return '$mode — $tested из $max тем · $questions вопросов';
  }

  @override
  String get resumeBtn => 'Продолжить';

  @override
  String get startOver => 'Начать заново';

  @override
  String get examPreparation => 'Подготовка к экзамену';

  @override
  String get gapsCheck => 'Проверка пробелов';

  @override
  String get examTitle => 'Экзамен';

  @override
  String get leaveExamTitle => 'Покинуть экзамен?';

  @override
  String get leaveExamContent =>
      'Таймер идёт! Если выйдешь, прогресс будет потерян.';

  @override
  String get examSubtitle => 'Реши задачи на время — как на настоящем НИШ';

  @override
  String get examSettings => 'Настройки';

  @override
  String get examProblems => 'Задач:';

  @override
  String get examTime => 'Время:';

  @override
  String examTimeMinutes(int minutes) {
    return '$minutes мин';
  }

  @override
  String get startExam => 'Начать экзамен';

  @override
  String problemNofM(int current, int total) {
    return 'Задача $current из $total';
  }

  @override
  String get excellent => 'Отлично!';

  @override
  String get canDoBetter => 'Можно лучше!';

  @override
  String timeLabel(String time) {
    return 'Время: $time';
  }

  @override
  String get result => 'Результат';

  @override
  String get skipped => 'Пропущено';

  @override
  String get oneMoreTime => 'Ещё раз';

  @override
  String get backBtn => 'Назад';

  @override
  String get graphTitle => 'Граф знаний';

  @override
  String get graphBtn => 'Граф';

  @override
  String get logoutTooltip => 'Выйти';

  @override
  String get legendMastered => 'Освоено';

  @override
  String get legendPartial => 'Частично';

  @override
  String get legendFailed => 'Провалено';

  @override
  String get legendUntested => 'Не проверено';

  @override
  String heroHello(String name) {
    return 'Привет, $name! 👋';
  }

  @override
  String get yourProgress => 'Твой прогресс';

  @override
  String topicsMastered(int mastered, int total) {
    return '$mastered из $total тем освоено';
  }

  @override
  String streakDays(int count, String day) {
    return '$count $day подряд';
  }

  @override
  String get day1 => 'день';

  @override
  String get day2to4 => 'дня';

  @override
  String get day5plus => 'дней';

  @override
  String get statMastered => 'Освоено';

  @override
  String get statSolved => 'Решено';

  @override
  String get statAccuracy => 'Точность';

  @override
  String get statAvgTime => 'Ср. время';

  @override
  String get dashboardDiagnostic => 'Диагностика';

  @override
  String get dashboardPractice => 'Практика';

  @override
  String get dashboardLeaderboard => 'Рейтинг';

  @override
  String get sectionsHeader => 'РАЗДЕЛЫ';

  @override
  String get tabTopics => 'Темы';

  @override
  String get tabProblems => 'Задачи';

  @override
  String sectionTestedOfTotal(int tested, int total) {
    return '$tested из $total проверено';
  }

  @override
  String sectionTopicsCount(int count) {
    return '$count тем';
  }

  @override
  String trainSection(String name) {
    return 'Тренировать: $name';
  }

  @override
  String get tapToPractice => 'Нажми чтобы практиковать';

  @override
  String get startLearning => 'Начать изучение';

  @override
  String get noSolvedProblems => 'Нет решённых задач';

  @override
  String get notSolvedYet => 'Ещё не решал';

  @override
  String get resumeBannerTitle => 'Незавершённая диагностика';

  @override
  String get resumeBannerSubtitle => 'Продолжи с того места, где остановился';

  @override
  String get resumeBannerBtn => 'Продолжить';

  @override
  String get retryBtn => 'Повторить';

  @override
  String get leaderboardTitle => '🏆 Лидерборд';

  @override
  String get sortByQuantity => 'По количеству';

  @override
  String get sortByAccuracy => 'По точности';

  @override
  String get sortByProgress => 'По прогрессу';

  @override
  String get itsYou => 'Это вы';

  @override
  String get reportTitle => 'Что не так?';

  @override
  String get reportErrorInProblem => 'Ошибка в условии';

  @override
  String get reportWrongAnswer => 'Неправильный ответ';

  @override
  String get reportUnclear => 'Непонятное условие';

  @override
  String get reportThanks => 'Спасибо! Мы проверим.';

  @override
  String get reportFailed => 'Не удалось отправить. Попробуйте позже.';

  @override
  String get reportTooltip => 'Пожаловаться';

  @override
  String get correctAnswer => 'Правильно! 🎉';

  @override
  String get incorrectAnswer => 'Неправильно';

  @override
  String get masteredBadge => 'Освоено';

  @override
  String get answerLabel => 'Ответ: ';

  @override
  String get solutionLabel => 'Решение:';

  @override
  String get masteryLabel => 'Освоение: ';

  @override
  String get yourAnswer => 'Ваш ответ';

  @override
  String get enterToAnswer => 'Enter — ответить';

  @override
  String get answerHint => 'Введите ответ...';

  @override
  String get submitAnswer => 'Ответить';

  @override
  String get skipBtn => 'Пропустить';

  @override
  String get page404 => '404';

  @override
  String get authTelegramError =>
      'Не удалось войти через Telegram. Попробуйте ещё раз.';

  @override
  String get authProfileError =>
      'Не удалось загрузить профиль. Попробуйте ещё раз.';

  @override
  String get practiceAnswerError => 'Не удалось отправить ответ';

  @override
  String get practiceProblemError => 'Не удалось загрузить задачу';

  @override
  String get diagnosticResumeError => 'Не удалось продолжить диагностику';

  @override
  String get diagnosticStartError => 'Не удалось начать диагностику';

  @override
  String get diagnosticAnswerError => 'Не удалось отправить ответ';

  @override
  String get diagnosticQuestionError => 'Не удалось загрузить вопрос';

  @override
  String get diagnosticFinishError => 'Не удалось завершить диагностику';

  @override
  String get dashboardLoadError => 'Не удалось загрузить данные';

  @override
  String get examStartError => 'Не удалось запустить экзамен';

  @override
  String get examAnswerError => 'Не удалось отправить ответ';

  @override
  String get leaderboardDefaultName => 'Ученик';
}
