import type { TaskState } from '../../lib/types'
import type { TagStatus } from '../../components/ApTag'

// Поддерживающий светофор (growth-mindset): ошибка — «где растёт мозг», без карающего тона.
// НИКОГДА не красный. Приоритет разбора задаёт цвет: «разберём» (самое важное) = primary
// (бренд-оранжевый, тянет взгляд), «почти» = info (синий, спокойнее), «готово» = success
// (зелёный). Слово-ярлык — НЕ-цветовой сигнал (a11y), плюс мягкие AA-подложки тагов.
interface StateMeta {
  /** Короткий статус-ярлык. */
  label: string
  /** Статус ApTag (фон/текст). */
  tag: TagStatus
}

export const STATE_META: Record<TaskState, StateMeta> = {
  revisit: { label: 'Разберём', tag: 'primary' },
  almost: { label: 'Почти', tag: 'info' },
  got: { label: 'Готово', tag: 'success' },
}

/** Порядок приоритета для триажа (сначала «разберём», в конце «готово»). */
export const STATE_PRIORITY: TaskState[] = ['revisit', 'almost', 'got']
