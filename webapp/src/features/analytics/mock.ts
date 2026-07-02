// Мок-аналитика для экрана «Прогресс»: топ повторяющихся типов ошибок ученика.
// Реальные ru микро-навыки уровня НИШ, отсортированы по убыванию error_count
// (первый — «в фокусе»). Зеркалит живой контракт /api/trainer/analytics (my_top).

import type { AnalyticsData } from '../../lib/types'

export const MOCK_ANALYTICS: AnalyticsData = {
  my_top: [
    {
      micro_skill: 'percent_base',
      label_ru: 'Проценты: путает базу',
      error_count: 9,
      last_cause_text: 'Снижение считал от старой цены, а не от новой.',
      node_id: 'PC02',
    },
    {
      micro_skill: 'fraction_common_denominator',
      label_ru: 'Дроби: общий знаменатель',
      error_count: 6,
      last_cause_text: 'Сложил числители, не приведя к общему знаменателю.',
      node_id: 'EQ04',
    },
    {
      micro_skill: 'sign_on_transfer',
      label_ru: 'Знаки при переносе',
      error_count: 5,
      last_cause_text: 'Перенёс слагаемое через «=», не сменив знак.',
      node_id: 'EQ04',
    },
    {
      micro_skill: 'order_of_operations',
      label_ru: 'Порядок действий',
      error_count: 3,
      last_cause_text: 'Сложение выполнил раньше умножения.',
      node_id: null,
    },
    {
      micro_skill: 'unit_conversion',
      label_ru: 'Перевод единиц',
      error_count: 2,
      last_cause_text: 'Минуты к часам перевёл умножением вместо деления.',
      node_id: null,
    },
  ],
}
