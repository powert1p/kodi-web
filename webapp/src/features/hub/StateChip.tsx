import type { CSSProperties } from 'react'
import type { TaskState } from '../../lib/types'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
}

// Поддерживающий мини-чип состояния: эмодзи + ярлык + затемнённый AA-текст
// на мягкой тонированной подложке. Плоский (без 3D-края) — это не действие.
// Цвет — НЕ единственный сигнал (есть эмодзи и слово).
export function StateChip({ state }: StateChipProps) {
  const meta = STATE_META[state]
  const style = {
    '--c': meta.accentVar,
    '--ci': meta.inkVar,
    backgroundColor: 'color-mix(in oklab, var(--c) 13%, white)',
    border: '1px solid color-mix(in oklab, var(--c) 28%, white)',
  } as CSSProperties

  return (
    <span
      style={style}
      className="inline-flex shrink-0 items-center gap-1 rounded-(--radius-pill) px-2.5 py-1 text-[0.72rem] font-extrabold text-(--ci)"
    >
      <span aria-hidden className="text-[0.8rem] leading-none">
        {meta.emoji}
      </span>
      {meta.label}
    </span>
  )
}
