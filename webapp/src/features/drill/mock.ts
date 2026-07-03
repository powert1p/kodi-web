// Мок-данные для чекпоинта дизайна Drill: одна задача-ошибка с РЕАЛЬНОЙ
// многошаговой лесенкой (проценты), ступень «попроще» для climb-down и
// мок-диагноз по фото. Заменяется реальным API/vision позже.

import type { WrongTask, Diagnosis, StepVerdict } from '../../lib/types'
import type { EasierRung } from '../../lib/ladder'

// Задача: «Цена 1200 ₽ выросла на 15%, затем снизилась на 10%».
// 4 шага: +15% → новая цена → −10% → итог. Ответы сверяются answersMatch().
export const MOCK_DRILL_TASK: WrongTask = {
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
}

// Варианты для шага «choose» (n=3). Правильный сверяется с expected_value.
export const STEP3_OPTIONS = ['новая', 'старая'] as const

// Ступень «попроще» (climb-down) на 2-ю ошибку оригинального шага.
export const MOCK_EASIER_RUNG: EasierRung = {
  instruction: 'Разогреемся: сколько будет $10\\%$ от $200$?',
  microSkill: 'Процент от числа · попроще',
  expected: '20',
}

// Мок-диагноз: vision «прочитал» фото и нашёл, где сломалось решение.
// failed_step указывает на шаг базы процента (считал −10% от старой цены).
export const MOCK_DIAGNOSIS: Diagnosis = {
  transcription:
    '1200 + 15% = 1380. Потом 1380 − 10% = 1242... но записал 1200 − 120 = 1080, затем 1080 + 180 = 1230.',
  failed_step: 3,
  cause_text:
    'Смотри: снижение на 10% ты посчитал от старой цены 1200, а не от новой 1380. После подорожания «база» меняется — от какой цены теперь считаем процент?',
  level: 3,
  micro_skill: 'База процента',
  micro_skill_label: 'База процента',
  confidence: 0.82,
  image_ref: 'mock://solution-photo',
}

// Мок-вердикт поэтапной сдачи (Блок 1.2): демонстрирует happy-path без бэка.
export const MOCK_STEP_VERDICT: StepVerdict = { verdict: 'match', hint: null, confidence: 0.9, step_n: 1 }
