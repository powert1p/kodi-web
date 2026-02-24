// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Kazakh (`kk`).
class AppLocalizationsKk extends AppLocalizations {
  AppLocalizationsKk([String locale = 'kk']) : super(locale);

  @override
  String get appTitle => 'NIS Math';

  @override
  String get tagArithmetic => 'Арифметика';

  @override
  String get tagFractions => 'Бөлшектер';

  @override
  String get tagDecimals => 'Ондық бөлшектер';

  @override
  String get tagDecimalsShort => 'Ондық';

  @override
  String get tagDivisibility => 'Бөлінгіштік';

  @override
  String get tagEquations => 'Теңдеулер';

  @override
  String get tagGeometry => 'Геометрия';

  @override
  String get tagAlgebra => 'Алгебра';

  @override
  String get tagWordProblems => 'Мәтінді есептер';

  @override
  String get tagWordProblemsShort => 'Мәтінді есептер';

  @override
  String get tagProportion => 'Пропорциялар';

  @override
  String get tagPercent => 'Пайыздар';

  @override
  String get tagRatios => 'Пропорциялар мен пайыздар';

  @override
  String get tagNumbers => 'Сандар';

  @override
  String get tagNumberTheory => 'Сандар теориясы';

  @override
  String get tagConversion => 'Өлшем бірліктері';

  @override
  String get tagConversionShort => 'Өлшем бірл.';

  @override
  String get tagMeasurement => 'Өлшем бірліктері';

  @override
  String get tagData => 'Деректер';

  @override
  String get tagDataAnalysis => 'Деректерді талдау';

  @override
  String get tagCombinatorics => 'Комбинаторика';

  @override
  String get tagProbability => 'Ықтималдық';

  @override
  String get tagStatistics => 'Статистика';

  @override
  String get tagModulus => 'Санның модулі';

  @override
  String get tagSequences => 'Тізбектер';

  @override
  String get tagSets => 'Жиындар';

  @override
  String get tagNegative => 'Теріс сандар';

  @override
  String get tagRounding => 'Дөңгелектеу';

  @override
  String get tagLogic => 'Логика';

  @override
  String onboardingHello(String name) {
    return 'Сәлем, $name! 👋';
  }

  @override
  String get onboardingWelcome =>
      'NIS Math-қа қош келдіңіз!\nМұнда сен НЗМ математика емтиханына дайындаласың.';

  @override
  String get onboardingStep1Title => 'Диагностикадан өт';

  @override
  String get onboardingStep1Subtitle =>
      '5-10 минут · жүйе сенің деңгейіңді анықтайды';

  @override
  String get onboardingStep2Title => 'Олқылықтарыңды біл';

  @override
  String get onboardingStep2Subtitle => 'AI сенің әлсіз жақтарыңды көрсетеді';

  @override
  String get onboardingStep3Title => 'Тақырыптар бойынша жаттығ';

  @override
  String get onboardingStep3Subtitle => '2525 есеп шешімдері мен суреттерімен';

  @override
  String get startDiagnostic => 'Диагностиканы бастау';

  @override
  String get examWithTimer => 'Таймермен емтихан';

  @override
  String get orJustSolve => 'Немесе жай есеп шығару →';

  @override
  String get loginSubtitle => 'НЗМ-ге түсуге дайындық';

  @override
  String get loginViaTelegram => 'Telegram арқылы кіру';

  @override
  String get loginOr => 'немесе';

  @override
  String get loginFooter => '2525 есеп · 118 тақырып · БКТ-алгоритм';

  @override
  String get phoneLabel => 'Телефон нөмірі';

  @override
  String get phoneHint => '+7 777 123 4567';

  @override
  String get phoneContinue => 'Жалғастыру';

  @override
  String get phoneEnterNumber => 'Телефон нөмірін енгізіңіз';

  @override
  String get phoneNewStudent => 'Жаңа оқушы! Атыңды жаз және PIN ойлап тап';

  @override
  String get phoneFoundNumber => 'Нөмір табылды! PIN кодты енгіз';

  @override
  String get phoneName => 'Аты';

  @override
  String get phoneNameHint => 'Сенің атың кім?';

  @override
  String get phoneCreatePin => 'PIN ойлап тап (4 сан)';

  @override
  String get phonePinCode => 'PIN-код';

  @override
  String get phonePinHint => '••••';

  @override
  String get phoneRegister => 'Тіркелу';

  @override
  String get phoneLogin => 'Кіру';

  @override
  String get phoneChangeNumber => 'Нөмірді өзгерту';

  @override
  String get phonePin4Digits => 'PIN — 4 сан';

  @override
  String get phoneEnterName => 'Атыңызды енгізіңіз';

  @override
  String get phoneCheckError =>
      'Нөмірді тексеру мүмкін болмады. Қайта көріңіз.';

  @override
  String get phoneLoginError => 'Кіру мүмкін болмады. Қайта көріңіз.';

  @override
  String get practiceTitle => 'Жаттығу';

  @override
  String get sessionStats => 'Сессия статистикасы';

  @override
  String get solved => 'Шешілді';

  @override
  String get correct => 'Дұрыс';

  @override
  String get accuracy => 'Дәлдік';

  @override
  String get avgTime => 'Орт. уақыт';

  @override
  String get maxCombo => 'Макс комбо';

  @override
  String get total => 'Барлығы';

  @override
  String get continueBtn => 'Жалғастыру';

  @override
  String get finishPracticeTitle => 'Жаттығуды аяқтау керек пе?';

  @override
  String finishPracticeContent(int count, int correct) {
    return 'Шешілген есептер: $count, дұрыс: $correct.';
  }

  @override
  String get exitBtn => 'Шығу';

  @override
  String get statisticsTooltip => 'Статистика';

  @override
  String get allSolved => 'Барлық есептер шешілді! 🎉';

  @override
  String get tryAnotherTopic => 'Басқа тақырыпты көр';

  @override
  String get goHome => 'Басты бетке';

  @override
  String get nextBtn => 'Келесі';

  @override
  String get arrowOrSpace => '→ немесе бос орын';

  @override
  String comboStreak(int count) {
    return '$count қатарынан!';
  }

  @override
  String get diagnosticTitle => 'Диагностика';

  @override
  String get leaveDiagnosticTitle => 'Диагностикадан шығу керек пе?';

  @override
  String get leaveDiagnosticContent =>
      'Прогресс сақталады — кейін жалғастыра аласыз.';

  @override
  String get stayBtn => 'Қалу';

  @override
  String get diagnosticKnowledge => 'Білім диагностикасы';

  @override
  String get diagnosticDescription =>
      '15 тақырып — адаптивті алгоритм саған есептерді таңдайды.';

  @override
  String get diagnosticExamMode => 'Емтиханға дайындалу';

  @override
  String get diagnosticExamSubtitle => '15 тақырып · 10-15 минут';

  @override
  String get diagnosticExamDescription =>
      'Күрделі тақырыптар бірінші — дайындығыңды тексер';

  @override
  String get diagnosticGapsMode => 'Олқылықтарды тексеру';

  @override
  String get diagnosticGapsSubtitle => '15 тақырып · 10-15 минут';

  @override
  String get diagnosticGapsDescription =>
      'Негізгі тақырыптардан жоғары — әлсіз жақтарыңды тап';

  @override
  String get startBtn => 'Бастау';

  @override
  String topicNofM(int current, int max) {
    return 'Тақырып $current / $max';
  }

  @override
  String nCorrect(int count) {
    return '$count дұрыс';
  }

  @override
  String get finishBtn => 'Аяқтау';

  @override
  String get diagnosticComplete => 'Диагностика аяқталды!';

  @override
  String get mastered => 'Меңгерілді';

  @override
  String get gaps => 'Олқылықтар';

  @override
  String get masteredTopics => 'Меңгерілген тақырыптар';

  @override
  String get weakTopics => 'Әлсіз тақырыптар';

  @override
  String get somethingWentWrong => 'Бірдеңе дұрыс болмады';

  @override
  String get tryAgain => 'Қайта көру';

  @override
  String get unfinishedDiagnostic => 'Аяқталмаған диагностика';

  @override
  String unfinishedDiagnosticInfo(
      String mode, int tested, int max, int questions) {
    return '$mode — $tested / $max тақырып · $questions сұрақ';
  }

  @override
  String get resumeBtn => 'Жалғастыру';

  @override
  String get startOver => 'Басынан бастау';

  @override
  String get examPreparation => 'Емтиханға дайындық';

  @override
  String get gapsCheck => 'Олқылықтарды тексеру';

  @override
  String get examTitle => 'Емтихан';

  @override
  String get leaveExamTitle => 'Емтиханнан шығу керек пе?';

  @override
  String get leaveExamContent =>
      'Таймер жүріп жатыр! Шықсаң, прогресс жоғалады.';

  @override
  String get examSubtitle => 'Есептерді уақытпен шеш — нағыз НЗМ сияқты';

  @override
  String get examSettings => 'Баптаулар';

  @override
  String get examProblems => 'Есептер:';

  @override
  String get examTime => 'Уақыт:';

  @override
  String examTimeMinutes(int minutes) {
    return '$minutes мин';
  }

  @override
  String get startExam => 'Емтиханды бастау';

  @override
  String problemNofM(int current, int total) {
    return 'Есеп $current / $total';
  }

  @override
  String get excellent => 'Тамаша!';

  @override
  String get canDoBetter => 'Жақсырақ болуы мүмкін!';

  @override
  String timeLabel(String time) {
    return 'Уақыт: $time';
  }

  @override
  String get result => 'Нәтиже';

  @override
  String get skipped => 'Өткізілді';

  @override
  String get oneMoreTime => 'Тағы бір рет';

  @override
  String get backBtn => 'Артқа';

  @override
  String get graphTitle => 'Білім графы';

  @override
  String get graphBtn => 'Граф';

  @override
  String get logoutTooltip => 'Шығу';

  @override
  String get legendMastered => 'Меңгерілді';

  @override
  String get legendPartial => 'Жартылай';

  @override
  String get legendFailed => 'Сәтсіз';

  @override
  String get legendUntested => 'Тексерілмеді';

  @override
  String heroHello(String name) {
    return 'Сәлем, $name! 👋';
  }

  @override
  String get yourProgress => 'Сенің прогресің';

  @override
  String topicsMastered(int mastered, int total) {
    return '$total тақырыптың $mastered меңгерілді';
  }

  @override
  String streakDays(int count, String day) {
    return 'Қатарынан $count $day';
  }

  @override
  String get day1 => 'күн';

  @override
  String get day2to4 => 'күн';

  @override
  String get day5plus => 'күн';

  @override
  String get statMastered => 'Меңгерілді';

  @override
  String get statSolved => 'Шешілді';

  @override
  String get statAccuracy => 'Дәлдік';

  @override
  String get statAvgTime => 'Орт. уақыт';

  @override
  String get dashboardDiagnostic => 'Диагностика';

  @override
  String get dashboardPractice => 'Жаттығу';

  @override
  String get dashboardLeaderboard => 'Рейтинг';

  @override
  String get sectionsHeader => 'БӨЛІМДЕР';

  @override
  String get tabTopics => 'Тақырыптар';

  @override
  String get tabProblems => 'Есептер';

  @override
  String sectionTestedOfTotal(int tested, int total) {
    return '$total ішінен $tested тексерілді';
  }

  @override
  String sectionTopicsCount(int count) {
    return '$count тақырып';
  }

  @override
  String trainSection(String name) {
    return 'Жаттығу: $name';
  }

  @override
  String get tapToPractice => 'Жаттығу үшін бас';

  @override
  String get startLearning => 'Оқуды бастау';

  @override
  String get noSolvedProblems => 'Шешілген есептер жоқ';

  @override
  String get notSolvedYet => 'Әлі шешкен жоқ';

  @override
  String get resumeBannerTitle => 'Аяқталмаған диагностика';

  @override
  String get resumeBannerSubtitle => 'Тоқтаған жерден жалғастыр';

  @override
  String get resumeBannerBtn => 'Жалғастыру';

  @override
  String get retryBtn => 'Қайталау';

  @override
  String get leaderboardTitle => '🏆 Көшбасшылар';

  @override
  String get sortByQuantity => 'Саны бойынша';

  @override
  String get sortByAccuracy => 'Дәлдігі бойынша';

  @override
  String get sortByProgress => 'Прогресс бойынша';

  @override
  String get itsYou => 'Бұл сіз';

  @override
  String get reportTitle => 'Не дұрыс емес?';

  @override
  String get reportErrorInProblem => 'Шартта қате бар';

  @override
  String get reportWrongAnswer => 'Жауап дұрыс емес';

  @override
  String get reportUnclear => 'Шарт түсініксіз';

  @override
  String get reportThanks => 'Рахмет! Біз тексереміз.';

  @override
  String get reportFailed => 'Жіберу мүмкін болмады. Кейінірек көріңіз.';

  @override
  String get reportTooltip => 'Шағымдану';

  @override
  String get correctAnswer => 'Дұрыс! 🎉';

  @override
  String get incorrectAnswer => 'Қате';

  @override
  String get masteredBadge => 'Меңгерілді';

  @override
  String get answerLabel => 'Жауап: ';

  @override
  String get solutionLabel => 'Шешімі:';

  @override
  String get masteryLabel => 'Меңгеру: ';

  @override
  String get yourAnswer => 'Сіздің жауабыңыз';

  @override
  String get enterToAnswer => 'Enter — жауап беру';

  @override
  String get answerHint => 'Жауапты енгізіңіз...';

  @override
  String get submitAnswer => 'Жауап беру';

  @override
  String get skipBtn => 'Өткізіп жіберу';

  @override
  String get page404 => '404';
}
