/// Unified tag label mappings used by dashboard and graph pages.
///
/// Replaces duplicate `_sectionNames` in dashboard_page.dart
/// and `_tagLabels` in graph_page.dart.
abstract final class TagLabels {
  /// Full labels for graph and detail views.
  static const full = <String, String>{
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

  /// Short labels for dashboard compact view.
  static const _short = <String, String>{
    'decimals': 'Десятичные',
    'word_problems': 'Текст. задачи',
    'conversion': 'Ед. измерения',
    'data': 'Данные',
  };

  /// Returns a label for [tag]. Uses short form when [compact] is true.
  static String label(String tag, {bool compact = false}) {
    if (compact) return _short[tag] ?? full[tag] ?? tag;
    return full[tag] ?? tag;
  }
}
