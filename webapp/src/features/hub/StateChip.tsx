import type { CSSProperties } from 'react'
import type { TaskState } from '../../lib/types'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
}

// Поддерживающий мини-чип: маскот-эмодзи + ярлык + затемнённый AA-текст на светлой подложке.
// Цвет — НЕ единственный сигнал (есть эмодзи и слово). Динамический токен через --c/--ci.
export function StateChip({ state }: StateChipProps) {
  const meta = STATE_META[state]
  const style = {
    '--c': meta.accentVar,
    '--ci': meta.inkVar,
    backgroundColor: 'color-mix(in oklab, var(--c) 14%, white)',
  } as CSSProperties

  return (
    <span
      style={style}
      className="clay-chip inline-flex shrink-0 items-center gap-1.5 rounded-(--radius-pill) px-2.5 py-1 text-[0.72rem] font-extrabold text-(--ci)"
    >
      <span aria-hidden className="text-[0.85rem] leading-none">
        {meta.emoji}
      </span>
      {meta.label}
    </span>
  )
}
