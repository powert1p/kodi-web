import type { TaskState } from '../../lib/types'
import type { TagStatus } from '../../components/ApTag'

// Поддерживающий светофор (growth-mindset): ошибка — «где растёт мозг», без карающего тона.
// НИКОГДА не красный. В палитре AiPlus: «разберём» = info (синий), «почти» = primary
// (бренд-оранжевый), «готово» = success (зелёный). Цвет — НЕ единственный сигнал
// (есть эмодзи и слово), плюс мягкие AA-подложки тагов.
interface StateMeta {
  /** Короткий статус-ярлык. */
  label: string
  /** Ободряющая микрокопия. */
  hint: string
  /** Мини-эмодзи настроения. */
  emoji: string
  /** Статус ApTag (фон/текст). */
  tag: TagStatus
  /** CSS-переменная акцентного цвета (точка состояния). */
  dotVar: string
}

export const STATE_META: Record<TaskState, StateMeta> = {
  revisit: {
    label: 'Разберём',
    hint: 'Здесь растёт мозг',
    emoji: '🔍',
    tag: 'info',
    dotVar: 'var(--text-info)',
  },
  almost: {
    label: 'Почти',
    hint: 'Один шаг до цели',
    emoji: '✨',
    tag: 'primary',
    dotVar: 'var(--bg-brand)',
  },
  got: {
    label: 'Готово',
    hint: 'Закрепим победу',
    emoji: '✅',
    tag: 'success',
    dotVar: 'var(--bg-success)',
  },
}

/** Порядок приоритета для триажа (сначала «разберём», в конце «готово»). */
export const STATE_PRIORITY: TaskState[] = ['revisit', 'almost', 'got']
