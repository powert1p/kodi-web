/// Unified tag label mappings used by dashboard and graph pages.
///
/// Replaces duplicate `_sectionNames` in dashboard_page.dart
/// and `_tagLabels` in graph_page.dart.
abstract final class TagLabels {
  /// Full labels for graph and detail views (Russian).
  static const _full = <String, String>{
    'arithmetic': 'Арифметика',
    'fractions': 'Дроби',
    'decimals': 'Десятичные дроби',
    'divisibility': 'Делимость',
    'equations': 'Уравнения',
    'geometry': 'Геометрия',
    'algebra': 'Алгебра',
    'word_problems': 'Текстовые задачи',
    'proportion': 'Пропорции',
    'percent': 'Проценты',
    'ratios': 'Пропорции и проценты',
    'numbers': 'Числа',
    'number_theory': 'Теория чисел',
    'conversion': 'Единицы измерения',
    'measurement': 'Единицы измерения',
    'data': 'Данные',
    'data_analysis': 'Анализ данных',
    'combinatorics': 'Комбинаторика',
    'probability': 'Вероятность',
    'statistics': 'Статистика',
    'modulus': 'Модуль числа',
    'sequences': 'Последовательности',
    'sets': 'Множества',
    'negative': 'Отрицательные числа',
    'rounding': 'Округление',
    'logic': 'Логика',
  };

  /// Full labels for Kazakh locale.
  static const _fullKz = <String, String>{
    'arithmetic': 'Арифметика',
    'fractions': 'Бөлшектер',
    'decimals': 'Ондық бөлшектер',
    'divisibility': 'Бөлінгіштік',
    'equations': 'Теңдеулер',
    'geometry': 'Геометрия',
    'algebra': 'Алгебра',
    'word_problems': 'Мәтінді есептер',
    'proportion': 'Пропорциялар',
    'percent': 'Пайыздар',
    'ratios': 'Пропорциялар мен пайыздар',
    'numbers': 'Сандар',
    'number_theory': 'Сандар теориясы',
    'conversion': 'Өлшем бірліктері',
    'measurement': 'Өлшем бірліктері',
    'data': 'Деректер',
    'data_analysis': 'Деректерді талдау',
    'combinatorics': 'Комбинаторика',
    'probability': 'Ықтималдық',
    'statistics': 'Статистика',
    'modulus': 'Санның модулі',
    'sequences': 'Тізбектер',
    'sets': 'Жиындар',
    'negative': 'Теріс сандар',
    'rounding': 'Дөңгелектеу',
    'logic': 'Логика',
  };

  /// Short labels for dashboard compact view.
  static const _short = <String, String>{
    'decimals': 'Десятичные',
    'word_problems': 'Текст. задачи',
    'conversion': 'Ед. измерения',
    'data': 'Данные',
  };

  /// Returns a label for [tag]. Uses short form when [compact] is true.
  /// When [locale] is 'kk', returns Kazakh labels.
  static String label(String tag, {bool compact = false, String locale = 'ru'}) {
    if (locale == 'kk') {
      return _fullKz[tag] ?? _full[tag] ?? tag;
    }
    if (compact) return _short[tag] ?? _full[tag] ?? tag;
    return _full[tag] ?? tag;
  }
}
