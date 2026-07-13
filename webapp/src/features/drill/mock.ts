// Мок-данные для чекпоинта дизайна Drill: одна задача-ошибка с РЕАЛЬНОЙ
// многошаговой лесенкой (проценты), ступень «попроще» для climb-down и
// мок-диагноз по фото. Заменяется реальным API/vision позже.

import type { WrongTask, StepVerdict } from '../../lib/types'
import type { EasierRung } from '../../lib/ladder'

// Задача: «Цена 1200 ₸ выросла на 15%, затем снизилась на 10%».
// 4 шага: +15% → новая цена → −10% → итог. Ответы сверяются answersMatch().
export const MOCK_DRILL_TASK: WrongTask = {
  id: 'wt-pc-01',
  problem_id: 4821,
  node_id: 'PC02',
  topic_label: 'Проценты',
  statement:
    'Цена товара $1200$ ₸ выросла на $15\\%$, а затем снизилась на $10\\%$. Найдите итоговую цену.',
  answer: '1242',
  primary_micro_skill: 'percent_of_change',
  primary_micro_skill_label: 'Изменение на процент',
  decomp_idx: 0,
  steps: [
    {
      n: 1,
      instruction_ru: 'Сколько тенге составляет рост на $15\\%$ от $1200$?',
      micro_skill: 'Процент от числа',
      micro_skill_label: 'Процент от числа',
      expected_value: '180',
      kind: 'compute',
      reveal: '$1200 \\cdot 0{,}15 = 180$ ₸ — это прибавка к цене.',
    },
    {
      n: 2,
      instruction_ru: 'Какой стала цена после роста?',
      micro_skill: 'Прибавить процент',
      micro_skill_label: 'Прибавить процент',
      expected_value: '1380',
      kind: 'compute',
      reveal: '$1200 + 180 = 1380$ ₸ — цена после подорожания.',
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
      reveal: '$1380 - 1380 \\cdot 0{,}1 = 1380 - 138 = 1242$ ₸.',
    },
  ],
  state: 'revisit',
  wrong_answer: '1230',
  mastery: 0.31,
  // Метод узла (форма = прод-данные): карточки PC «Проценты» в банке ещё нет,
  // текст в регистре боевых cards-*.json (совпадает с hub/mock wt-pc-01).
  theory_ru:
    '**Метод** — Каждый процент считается от АКТУАЛЬНОЙ величины, а не от начальной. При росте на p% умножай на (1 + p/100), при снижении — на (1 − p/100). Несколько изменений подряд применяй по очереди: результат первого становится базой для второго.\n\n**Пример** — 200 выросло на 10%: 200 × 1,1 = 220. Затем снизилось на 10%: 220 × 0,9 = 198 (не 200!).\n\n**Ловушка** — второе изменение считают от начальной цены, а не от новой — поэтому «+10%, потом −10%» ошибочно возвращает к старому числу.',
}

// Варианты для шага «choose» (n=3). Правильный сверяется с expected_value.
export const STEP3_OPTIONS = ['новая', 'старая'] as const

// Ступень «попроще» (climb-down) на 2-ю ошибку оригинального шага.
export const MOCK_EASIER_RUNG: EasierRung = {
  instruction: 'Разогреемся: сколько будет $10\\%$ от $200$?',
  microSkill: 'Процент от числа · попроще',
  expected: '20',
}

// Мок-вердикт поэтапной сдачи (Блок 1.2): демонстрирует happy-path без бэка.
export const MOCK_STEP_VERDICT: StepVerdict = { verdict: 'match', hint: null, confidence: 0.9, step_n: 1 }
