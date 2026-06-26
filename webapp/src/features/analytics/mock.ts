// Мок-аналитика для экрана «Прогресс»: топ повторяющихся типов ошибок ученика.
// Реальные ru микро-навыки уровня НИШ, отсортированы по убыванию count
// (первый — «в фокусе»). Заменяется живым /api/trainer/analytics позже.

import type { AnalyticsData } from '../../lib/types'

export const MOCK_ANALYTICS: AnalyticsData = {
  error_types: [
    {
      micro_skill: 'percent_base',
      label: 'Проценты: путает базу',
      topic_label: 'Проценты',
      count: 9,
      last_cause: 'Снижение считал от старой цены, а не от новой.',
    },
    {
      micro_skill: 'fraction_common_denominator',
      label: 'Дроби: общий знаменатель',
      topic_label: 'Дроби',
      count: 6,
      last_cause: 'Сложил числители, не приведя к общему знаменателю.',
    },
    {
      micro_skill: 'sign_on_transfer',
      label: 'Знаки при переносе',
      topic_label: 'Уравнения',
      count: 5,
      last_cause: 'Перенёс слагаемое через «=», не сменив знак.',
    },
    {
      micro_skill: 'order_of_operations',
      label: 'Порядок действий',
      topic_label: 'Выражения',
      count: 3,
      last_cause: 'Сложение выполнил раньше умножения.',
    },
    {
      micro_skill: 'unit_conversion',
      label: 'Перевод единиц',
      topic_label: 'Величины',
      count: 2,
      last_cause: 'Минуты к часам перевёл умножением вместо деления.',
    },
  ],
}
