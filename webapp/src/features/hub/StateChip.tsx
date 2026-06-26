import type { CSSProperties } from 'react'
import type { TaskState } from '../../lib/types'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
}

// Чип состояния. Цвет берётся из токена через CSS-переменную --c
// (динамический токен — допустимый кейс для style, литералов hex/px тут нет).
export function StateChip({ state }: StateChipProps) {
  const meta = STATE_META[state]
  const style = { '--c': meta.accentVar } as CSSProperties

  return (
    <span
      style={style}
      className="inline-flex items-center gap-1.5 rounded-(--radius-chip) border border-[color-mix(in_oklab,var(--c)_45%,transparent)] bg-[color-mix(in_oklab,var(--c)_14%,transparent)] px-2.5 py-1 text-[0.7rem] font-semibold uppercase tracking-wider text-(--c)"
    >
      <span className="size-1.5 rounded-full bg-(--c)" />
      {meta.label}
    </span>
  )
}
