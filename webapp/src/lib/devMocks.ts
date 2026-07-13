// DEV-фикстуры (бэкенд недоступен локально) — тот же паттерн, что fetchWrongTasks/fetchMe.
// Используются ТОЛЬКО в import.meta.env.DEV && MODE !== 'test' (см. api.ts): живые
// скриншоты/ручная проверка экранов среза/прогресса/закрепления без поднятого бэка.
// Форма = прод-контракт (BE-схемы); НЕ участвуют в тестах.

import type {
  SrezTask,
  AnalyticsData,
  ProblemTopic,
  VerificationProblemDTO,
} from './types'

// 12 задач мини-среза вразброс тем (форма BE SrezTask). Правильный ответ на клиент
// НЕ приходит — как в проде (§2.5). answer_type информирует только серверную проверку.
export const MOCK_SREZ_TASKS: SrezTask[] = [
  { problem_id: 9001, node_title: 'Цифры числа (разряды, количество)', statement: 'Найдите двузначное число, если оно равно удвоенному произведению своих цифр.', answer_type: 'number', position: 1, total: 12 },
  { problem_id: 9002, node_title: 'Проценты', statement: 'Какое число составляет $40\\%$ от $250$?', answer_type: 'number', position: 2, total: 12 },
  { problem_id: 9003, node_title: 'Дроби', statement: 'Вычислите: $\\dfrac{3}{4} + \\dfrac{1}{6}$.', answer_type: 'fraction', position: 3, total: 12 },
  { problem_id: 9004, node_title: 'Линейные уравнения', statement: 'Решите уравнение $3(x - 4) = 2x + 5$.', answer_type: 'number', position: 4, total: 12 },
  { problem_id: 9005, node_title: 'Площадь', statement: 'Найдите площадь прямоугольного треугольника с катетами $6$ и $8$.', answer_type: 'number', position: 5, total: 12 },
  { problem_id: 9006, node_title: 'Модуль числа', statement: 'Уравнение $|x - 3| = 5$. Найдите произведение корней.', answer_type: 'number', position: 6, total: 12 },
  { problem_id: 9007, node_title: 'Концентрация (смеси)', statement: 'Из $300$ г $20\\%$-го раствора выпарили $100$ г воды. Какова концентрация?', answer_type: 'number', position: 7, total: 12 },
  { problem_id: 9008, node_title: 'Системы уравнений', statement: '2 тетради и 3 ручки стоят $240$ тенге. 1 тетрадь и 2 ручки — $140$. Сколько стоит ручка?', answer_type: 'number', position: 8, total: 12 },
  { problem_id: 9009, node_title: 'Степени', statement: 'Вычислите $2^5 - 2^3$.', answer_type: 'number', position: 9, total: 12 },
  { problem_id: 9010, node_title: 'НОД и НОК', statement: 'Найдите НОК чисел $6$ и $9$.', answer_type: 'number', position: 10, total: 12 },
  { problem_id: 9011, node_title: 'Периметр', statement: 'Периметр квадрата $36$ см. Найдите его сторону.', answer_type: 'number', position: 11, total: 12 },
  { problem_id: 9012, node_title: 'Пропорции', statement: 'За $3$ часа насос перекачал $180$ л. Сколько литров за $5$ часов?', answer_type: 'number', position: 12, total: 12 },
]

// Топ повторяющихся ошибок (BE AnalyticsResponse.my_top).
export const MOCK_ANALYTICS: AnalyticsData = {
  my_top: [
    { micro_skill: 'percent_base', label_ru: 'База процента', error_count: 7, last_cause_text: 'посчитал скидку от старой цены, а не от новой', node_id: 'PC02' },
    { micro_skill: 'common_denominator', label_ru: 'Общий знаменатель', error_count: 5, last_cause_text: 'перемножил знаменатели вместо НОК', node_id: 'FR04' },
    { micro_skill: 'distribute_terms', label_ru: 'Раскрытие скобок', error_count: 4, last_cause_text: null, node_id: 'LE01' },
    { micro_skill: 'system_setup', label_ru: 'Составление системы', error_count: 3, last_cause_text: null, node_id: 'SE01' },
    { micro_skill: 'triangle_area', label_ru: 'Площадь треугольника', error_count: 2, last_cause_text: null, node_id: 'AR03' },
  ],
}

// Проблемные темы (BE ProblemTopicOut).
export const MOCK_PROBLEM_TOPICS: ProblemTopic[] = [
  { topic_id: 'PC', strand: 'Числа', name_ru: 'Проценты', error_count: 9, top_micro_skills: [], nodes_mastery_avg: 0.34, closure_progress: 0.25 },
  { topic_id: 'FR', strand: 'Числа', name_ru: 'Дроби', error_count: 6, top_micro_skills: [], nodes_mastery_avg: 0.52, closure_progress: 0.5 },
  { topic_id: 'LE', strand: 'Алгебра', name_ru: 'Линейные уравнения', error_count: 4, top_micro_skills: [], nodes_mastery_avg: 0.61, closure_progress: 0.66 },
]

// Контрольная закрепления (BE VerificationProblemDTO).
export const MOCK_VERIFICATION: VerificationProblemDTO = {
  problem_id: 4899,
  node_id: 'PC02',
  topic_label: 'Проценты',
  statement: 'Цена $800$ ₸ выросла на $25\\%$, затем снизилась на $20\\%$. Найдите итоговую цену.',
  micro_skill: 'percent_of_change',
  micro_skill_label: 'Изменение на процент',
  xp: 30,
}
