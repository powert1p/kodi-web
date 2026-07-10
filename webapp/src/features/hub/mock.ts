import type { WrongTask } from '../../lib/types'

// Мок-фикстура для чекпоинта дизайна: реалистичные русско-математические задачи
// с инлайн-LaTeX, разные темы и состояния-светофора. Заменяется реальным API позже.
export const MOCK_WRONG_TASKS: WrongTask[] = [
  {
    id: 'wt-pc-01',
    problem_id: 4821,
    node_id: 'PC02',
    topic_label: 'Проценты',
    statement:
      'Цена товара $1200$ ₽ выросла на $15\\%$, а затем снизилась на $10\\%$. Найдите итоговую цену.',
    answer: '1242',
    primary_micro_skill: 'percent_of_change',
    primary_micro_skill_label: 'Изменение на процент',
    decomp_idx: 0,
    // Ступени приходят с боевой wrong-task (drill читает task.steps напрямую).
    // В DEV-фикстуре держим их у эталонной задачи «Проценты» — иначе drill без
    // лесенки и без единственного входа сдачи (после удаления нижнего фото).
    steps: [
      {
        n: 1,
        instruction_ru: 'Сколько рублей составляет рост на $15\\%$ от $1200$?',
        micro_skill: 'Процент от числа',
        micro_skill_label: 'Процент от числа',
        expected_value: '180',
        kind: 'compute',
        reveal: '$1200 \\cdot 0{,}15 = 180$ ₽ — это прибавка к цене.',
      },
      {
        n: 2,
        instruction_ru: 'Какой стала цена после роста?',
        micro_skill: 'Прибавить процент',
        micro_skill_label: 'Прибавить процент',
        expected_value: '1380',
        kind: 'compute',
        reveal: '$1200 + 180 = 1380$ ₽ — цена после подорожания.',
      },
      {
        n: 3,
        instruction_ru:
          'Снижение на $10\\%$ считаем от НОВОЙ цены $1380$ или от старой $1200$?',
        micro_skill: 'База процента',
        micro_skill_label: 'База процента',
        expected_value: 'новая',
        kind: 'choose',
        reveal: 'От новой: $1380$. Каждый процент считается от актуальной цены.',
      },
      {
        n: 4,
        instruction_ru: 'Сколько получится после снижения на $10\\%$ от $1380$?',
        micro_skill: 'Вычесть процент',
        micro_skill_label: 'Вычесть процент',
        expected_value: '1242',
        kind: 'compute',
        reveal: '$1380 - 1380 \\cdot 0{,}1 = 1380 - 138 = 1242$ ₽.',
      },
    ],
    state: 'revisit',
    wrong_answer: '1230',
    mastery: 0.31,
  },
  {
    id: 'wt-fr-02',
    problem_id: 5093,
    node_id: 'FR04',
    topic_label: 'Дроби',
    statement:
      'Вычислите: $\\dfrac{3}{4} + \\dfrac{5}{6} - \\dfrac{2}{3}$.',
    answer: '11/12',
    primary_micro_skill: 'common_denominator',
    primary_micro_skill_label: 'Общий знаменатель',
    decomp_idx: 1,
    steps: [],
    state: 'almost',
    wrong_answer: '13/12',
    mastery: 0.58,
  },
  {
    id: 'wt-le-03',
    problem_id: 6210,
    node_id: 'LE01',
    topic_label: 'Линейные уравнения',
    statement:
      'Решите уравнение $3(x - 4) = 2x + 5$ и найдите $x$.',
    answer: '17',
    primary_micro_skill: 'distribute_terms',
    primary_micro_skill_label: 'Раскрытие скобок',
    decomp_idx: 0,
    steps: [],
    state: 'almost',
    wrong_answer: '13',
    mastery: 0.62,
  },
  {
    id: 'wt-ar-04',
    problem_id: 7355,
    node_id: 'AR03',
    topic_label: 'Площадь',
    statement:
      'Найдите площадь прямоугольного треугольника с катетами $6$ см и $8$ см.',
    answer: '24',
    primary_micro_skill: 'triangle_area',
    primary_micro_skill_label: 'Площадь треугольника',
    decomp_idx: 2,
    steps: [],
    state: 'got',
    wrong_answer: '48',
    mastery: 0.84,
  },
  {
    id: 'wt-pc-05',
    problem_id: 4477,
    node_id: 'PC05',
    topic_label: 'Проценты',
    statement:
      'Какое число составляет $40\\%$ от $250$?',
    answer: '100',
    primary_micro_skill: 'percent_of_number',
    primary_micro_skill_label: 'Процент от числа',
    decomp_idx: 0,
    steps: [],
    state: 'revisit',
    wrong_answer: '62.5',
    mastery: 0.22,
  },
]
