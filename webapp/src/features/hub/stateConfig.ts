import type { TaskState } from '../../lib/types'

// Поддерживающий светофор: ошибка — «где растёт мозг», без карающего тона.
// label — короткий статус, hint — ободряющая микрокопия.
interface StateMeta {
  label: string
  hint: string
  /** CSS-переменная цвета акцента (лейн-полоса, чип). */
  accentVar: string
  dimVar: string
}

export const STATE_META: Record<TaskState, StateMeta> = {
  revisit: {
    label: 'Вернуться',
    hint: 'Здесь растёт мозг',
    accentVar: 'var(--color-revisit)',
    dimVar: 'var(--color-revisit-dim)',
  },
  almost: {
    label: 'Почти',
    hint: 'Один шаг до цели',
    accentVar: 'var(--color-almost)',
    dimVar: 'var(--color-almost-dim)',
  },
  got: {
    label: 'Разобрал',
    hint: 'Закрепи победу',
    accentVar: 'var(--color-got)',
    dimVar: 'var(--color-got-dim)',
  },
}
