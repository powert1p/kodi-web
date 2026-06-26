import type { TaskState } from '../../lib/types'
import { ApTag } from '../../components/ApTag'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
  className?: string
}

// Поддерживающий мини-таг состояния (AiPlus ApTag): ярлык-слово на мягкой
// тонированной подложке. Плоский — это не действие. Цвет НЕ единственный сигнал
// (слово-ярлык несёт смысл без цвета).
export function StateChip({ state, className }: StateChipProps) {
  const meta = STATE_META[state]
  return (
    <ApTag status={meta.tag} className={className}>
      {meta.label}
    </ApTag>
  )
}
