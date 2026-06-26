import type { TaskState } from '../../lib/types'

// Поддерживающий светофор (growth-mindset): ошибка — «где растёт мозг», без карающего тона.
// label — короткий статус, hint — ободряющая микрокопия, emoji — мини-маскот настроения.
interface StateMeta {
  label: string
  hint: string
  /** Маскот-эмодзи (цвет — не единственный сигнал). */
  emoji: string
  /** CSS-переменная акцентного цвета (точка/обводка чипа). */
  accentVar: string
  /** Переменная затемнённого цвета для AA-текста на светлом чипе. */
  inkVar: string
}

export const STATE_META: Record<TaskState, StateMeta> = {
  revisit: {
    label: 'Разберём',
    hint: 'Здесь растёт мозг',
    emoji: '🌱',
    accentVar: 'var(--color-revisit)',
    inkVar: 'var(--color-revisit-ink)',
  },
  almost: {
    label: 'Почти',
    hint: 'Один шаг до цели',
    emoji: '✨',
    accentVar: 'var(--color-almost)',
    inkVar: 'var(--color-almost-ink)',
  },
  got: {
    label: 'Готово',
    hint: 'Закрепим победу',
    emoji: '💪',
    accentVar: 'var(--color-got)',
    inkVar: 'var(--color-got-ink)',
  },
}

/** Порядок приоритета для триажа и для цвета дуги hero-кольца. */
export const STATE_PRIORITY: TaskState[] = ['revisit', 'almost', 'got']
