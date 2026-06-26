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
    decomp_idx: 0,
    steps: [],
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
    decomp_idx: 0,
    steps: [],
    state: 'revisit',
    wrong_answer: '62.5',
    mastery: 0.22,
  },
]
