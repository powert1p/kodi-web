// Мок-«контрольная» для закрепления: тот же навык (проценты от числа),
// НОВЫЕ числа относительно drill-задачи. Ученик решает БЕЗ подсказок —
// верный ответ закрывает ошибку. Заменяется backend `pick_verification_problem`
// (GET /api/trainer/verification?task=…) позже.

/** Контрольная задача на закрепление навыка. */
export interface VerificationProblem {
  /** Узел/навык, который закрепляем. */
  node_id: string
  topic_label: string
  micro_skill: string
  /** Условие; инлайн-LaTeX в $...$. */
  statement: string
  /** Эталон для answersMatch (поддержка дробей/запятой). */
  expected: string
  /** Единица для подписи ответа (₽, см…), либо ''. */
  unit: string
  /** Награда за закрытие. */
  xp: number
}

// Тот же навык «процент от числа со сменой базы», что и drill (PC02),
// но числа другие: 800 ₽ выросла на 20%, затем снизилась на 5% → 912.
export const MOCK_VERIFICATION: VerificationProblem = {
  node_id: 'PC02',
  topic_label: 'Проценты',
  micro_skill: 'Процент со сменой базы',
  statement:
    'Цена $800$ ₽ выросла на $20\\%$, а потом снизилась на $5\\%$. Сколько стала стоить? (без подсказок)',
  expected: '912',
  unit: '₽',
  xp: 30,
}
